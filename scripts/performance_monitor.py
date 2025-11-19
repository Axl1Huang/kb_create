#!/usr/bin/env python3
"""
并行处理监控和性能分析工具
实时监控双显卡处理状态，提供性能优化建议
"""

import sys
import time
import json
import logging
import psutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import threading
from datetime import datetime
import signal

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.monitoring = False
        self.monitor_thread = None
        self.data = []
        self.lock = threading.Lock()
        
        # 创建监控日志文件
        self.monitor_log = log_dir / f"performance_monitor_{int(time.time())}.jsonl"
        self.alerts_log = log_dir / f"performance_alerts_{int(time.time())}.jsonl"
        
        # 性能阈值
        self.thresholds = {
            "cpu_percent": 85,
            "memory_percent": 90,
            "disk_percent": 85,
            "gpu_memory_percent": 90,
            "gpu_temperature": 80,
            "process_queue_size": 1000,
            "processing_time_per_pdf": 60  # 秒
        }
    
    def get_system_metrics(self) -> Dict:
        """获取系统指标"""
        try:
            # CPU和内存
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            # 进程信息
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 1 or proc_info['memory_percent'] > 1:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # GPU信息
            gpu_metrics = self.get_gpu_metrics()
            
            return {
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory.percent,
                    "used_gb": memory.used / (1024**3)
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": disk.percent,
                    "used_gb": disk.used / (1024**3)
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                },
                "processes": processes,
                "gpu": gpu_metrics
            }
        except Exception as e:
            logging.error(f"获取系统指标失败: {e}")
            return {"error": str(e)}
    
    def get_gpu_metrics(self) -> Dict:
        """获取GPU指标"""
        gpu_metrics = {}
        
        try:
            # 使用nvidia-smi获取GPU信息
            result = subprocess.run([
                "nvidia-smi", 
                "--query-gpu=index,name,memory.total,memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu",
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split(', ')
                    if len(parts) >= 8:
                        gpu_id = int(parts[0])
                        gpu_metrics[f"gpu_{gpu_id}"] = {
                            "name": parts[1],
                            "memory_total_mb": int(parts[2]),
                            "memory_used_mb": int(parts[3]),
                            "memory_free_mb": int(parts[4]),
                            "temperature_c": float(parts[5]) if parts[5] != "[N/A]" else None,
                            "power_draw_w": float(parts[6]) if parts[6] != "[N/A]" else None,
                            "utilization_percent": float(parts[7]) if parts[7] != "[N/A]" else None,
                            "memory_utilization_percent": (int(parts[3]) / int(parts[2])) * 100 if parts[2] != "0" else 0
                        }
        except Exception as e:
            logging.error(f"获取GPU指标失败: {e}")
        
        return gpu_metrics
    
    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """检查性能警报"""
        alerts = []
        
        # CPU警报
        if metrics.get("cpu", {}).get("percent", 0) > self.thresholds["cpu_percent"]:
            alerts.append({
                "level": "warning",
                "type": "cpu_high",
                "message": f"CPU使用率过高: {metrics['cpu']['percent']:.1f}%",
                "value": metrics["cpu"]["percent"],
                "threshold": self.thresholds["cpu_percent"]
            })
        
        # 内存警报
        if metrics.get("memory", {}).get("percent", 0) > self.thresholds["memory_percent"]:
            alerts.append({
                "level": "critical",
                "type": "memory_high",
                "message": f"内存使用率过高: {metrics['memory']['percent']:.1f}%",
                "value": metrics["memory"]["percent"],
                "threshold": self.thresholds["memory_percent"]
            })
        
        # 磁盘警报
        if metrics.get("disk", {}).get("percent", 0) > self.thresholds["disk_percent"]:
            alerts.append({
                "level": "warning",
                "type": "disk_high",
                "message": f"磁盘使用率过高: {metrics['disk']['percent']:.1f}%",
                "value": metrics["disk"]["percent"],
                "threshold": self.thresholds["disk_percent"]
            })
        
        # GPU警报
        for gpu_name, gpu_data in metrics.get("gpu", {}).items():
            if gpu_data.get("memory_utilization_percent", 0) > self.thresholds["gpu_memory_percent"]:
                alerts.append({
                    "level": "warning",
                    "type": "gpu_memory_high",
                    "message": f"{gpu_name} 显存使用率过高: {gpu_data['memory_utilization_percent']:.1f}%",
                    "value": gpu_data["memory_utilization_percent"],
                    "threshold": self.thresholds["gpu_memory_percent"],
                    "gpu": gpu_name
                })
            
            if gpu_data.get("temperature_c") and gpu_data["temperature_c"] > self.thresholds["gpu_temperature"]:
                alerts.append({
                    "level": "warning",
                    "type": "gpu_temperature_high",
                    "message": f"{gpu_name} 温度过高: {gpu_data['temperature_c']:.1f}°C",
                    "value": gpu_data["temperature_c"],
                    "threshold": self.thresholds["gpu_temperature"],
                    "gpu": gpu_name
                })
        
        return alerts
    
    def monitor_loop(self, interval: int = 30):
        """监控循环"""
        while self.monitoring:
            try:
                # 获取指标
                metrics = self.get_system_metrics()
                
                # 检查警报
                alerts = self.check_alerts(metrics)
                
                # 保存数据
                with self.lock:
                    self.data.append(metrics)
                    
                    # 写入监控日志
                    with open(self.monitor_log, "a") as f:
                        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")
                    
                    # 写入警报日志
                    if alerts:
                        with open(self.alerts_log, "a") as f:
                            for alert in alerts:
                                f.write(json.dumps(alert, ensure_ascii=False) + "\n")
                
                # 输出警报
                for alert in alerts:
                    if alert["level"] == "critical":
                        logging.critical(alert["message"])
                    else:
                        logging.warning(alert["message"])
                
                time.sleep(interval)
                
            except Exception as e:
                logging.error(f"监控循环错误: {e}")
                time.sleep(interval)
    
    def start_monitoring(self, interval: int = 30):
        """开始监控"""
        if self.monitoring:
            logging.warning("监控已在运行")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, args=(interval,))
        self.monitor_thread.start()
        logging.info(f"性能监控已启动，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        logging.info("性能监控已停止")
    
    def generate_report(self, duration_hours: float = 1.0) -> Dict:
        """生成性能报告"""
        with self.lock:
            if not self.data:
                return {"error": "没有监控数据"}
            
            # 过滤最近的数据
            cutoff_time = time.time() - (duration_hours * 3600)
            recent_data = [d for d in self.data if d["timestamp"] > cutoff_time]
            
            if not recent_data:
                return {"error": "指定时间段内没有数据"}
            
            # 计算统计信息
            cpu_values = [d["cpu"]["percent"] for d in recent_data if "cpu" in d]
            memory_values = [d["memory"]["percent"] for d in recent_data if "memory" in d]
            disk_values = [d["disk"]["percent"] for d in recent_data if "disk" in d]
            
            gpu_stats = {}
            for data in recent_data:
                for gpu_name, gpu_data in data.get("gpu", {}).items():
                    if gpu_name not in gpu_stats:
                        gpu_stats[gpu_name] = {
                            "memory_utilization": [],
                            "temperature": [],
                            "utilization": []
                        }
                    
                    if "memory_utilization_percent" in gpu_data:
                        gpu_stats[gpu_name]["memory_utilization"].append(gpu_data["memory_utilization_percent"])
                    
                    if "temperature_c" in gpu_data and gpu_data["temperature_c"] is not None:
                        gpu_stats[gpu_name]["temperature"].append(gpu_data["temperature_c"])
                    
                    if "utilization_percent" in gpu_data and gpu_data["utilization_percent"] is not None:
                        gpu_stats[gpu_name]["utilization"].append(gpu_data["utilization_percent"])
            
            # 生成报告
            report = {
                "duration_hours": duration_hours,
                "data_points": len(recent_data),
                "system_stats": {
                    "cpu": {
                        "avg_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                        "max_percent": max(cpu_values) if cpu_values else 0,
                        "min_percent": min(cpu_values) if cpu_values else 0
                    },
                    "memory": {
                        "avg_percent": sum(memory_values) / len(memory_values) if memory_values else 0,
                        "max_percent": max(memory_values) if memory_values else 0,
                        "min_percent": min(memory_values) if memory_values else 0
                    },
                    "disk": {
                        "avg_percent": sum(disk_values) / len(disk_values) if disk_values else 0,
                        "max_percent": max(disk_values) if disk_values else 0,
                        "min_percent": min(disk_values) if disk_values else 0
                    }
                },
                "gpu_stats": {}
            }
            
            # GPU统计
            for gpu_name, stats in gpu_stats.items():
                report["gpu_stats"][gpu_name] = {
                    "memory_utilization": {
                        "avg": sum(stats["memory_utilization"]) / len(stats["memory_utilization"]) if stats["memory_utilization"] else 0,
                        "max": max(stats["memory_utilization"]) if stats["memory_utilization"] else 0,
                        "min": min(stats["memory_utilization"]) if stats["memory_utilization"] else 0
                    },
                    "temperature": {
                        "avg": sum(stats["temperature"]) / len(stats["temperature"]) if stats["temperature"] else 0,
                        "max": max(stats["temperature"]) if stats["temperature"] else 0,
                        "min": min(stats["temperature"]) if stats["temperature"] else 0
                    } if stats["temperature"] else None,
                    "utilization": {
                        "avg": sum(stats["utilization"]) / len(stats["utilization"]) if stats["utilization"] else 0,
                        "max": max(stats["utilization"]) if stats["utilization"] else 0,
                        "min": min(stats["utilization"]) if stats["utilization"] else 0
                    } if stats["utilization"] else None
                }
            
            # 性能分析
            report["performance_analysis"] = self.analyze_performance(report)
            
            return report
    
    def analyze_performance(self, report: Dict) -> Dict:
        """分析性能"""
        analysis = {
            "bottlenecks": [],
            "recommendations": [],
            "efficiency_score": 0
        }
        
        # 分析系统瓶颈
        if report["system_stats"]["cpu"]["avg_percent"] > 80:
            analysis["bottlenecks"].append("CPU使用率持续较高")
            analysis["recommendations"].append("考虑增加CPU核心或优化处理算法")
        
        if report["system_stats"]["memory"]["avg_percent"] > 85:
            analysis["bottlenecks"].append("内存使用率过高")
            analysis["recommendations"].append("考虑增加内存或优化内存使用")
        
        if report["system_stats"]["disk"]["avg_percent"] > 80:
            analysis["bottlenecks"].append("磁盘I/O可能成为瓶颈")
            analysis["recommendations"].append("考虑使用SSD或优化磁盘访问模式")
        
        # GPU分析
        for gpu_name, gpu_stats in report["gpu_stats"].items():
            if gpu_stats["memory_utilization"]["avg"] > 85:
                analysis["bottlenecks"].append(f"{gpu_name} 显存使用率过高")
                analysis["recommendations"].append(f"考虑优化{gpu_name}的显存使用或增加显存")
            
            if gpu_stats.get("temperature") and gpu_stats["temperature"]["max"] > 75:
                analysis["bottlenecks"].append(f"{gpu_name} 温度过高")
                analysis["recommendations"].append(f"考虑改善{gpu_name}的散热条件")
        
        # 计算效率分数
        efficiency_factors = [
            100 - min(report["system_stats"]["cpu"]["avg_percent"], 100),
            100 - min(report["system_stats"]["memory"]["avg_percent"], 100),
            100 - min(report["system_stats"]["disk"]["avg_percent"], 100)
        ]
        
        # 添加GPU效率
        for gpu_stats in report["gpu_stats"].values():
            efficiency_factors.append(100 - min(gpu_stats["memory_utilization"]["avg"], 100))
        
        analysis["efficiency_score"] = sum(efficiency_factors) / len(efficiency_factors)
        
        return analysis

def main():
    parser = argparse.ArgumentParser(description="并行处理监控和性能分析工具")
    parser.add_argument("--monitor", action="store_true", help="启动监控模式")
    parser.add_argument("--interval", type=int, default=30, help="监控间隔(秒)")
    parser.add_argument("--duration", type=float, default=1.0, help="报告时长(小时)")
    parser.add_argument("--report-file", type=Path, help="报告输出文件")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    
    args = parser.parse_args()
    
    # 配置
    config = Config()
    config.setup_directories()
    
    log_file = config.paths.logs_dir / "performance_monitor.log"
    setup_logging(log_file, args.log_level)
    
    monitor = PerformanceMonitor(config.paths.logs_dir)
    
    if args.monitor:
        # 启动监控
        logging.info("启动性能监控...")
        monitor.start_monitoring(args.interval)
        
        # 处理中断信号
        def signal_handler(sig, frame):
            logging.info("收到中断信号，停止监控...")
            monitor.stop_monitoring()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # 保持运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop_monitoring()
    
    else:
        # 生成报告
        logging.info(f"生成长达 {args.duration} 小时的性能报告...")
        report = monitor.generate_report(args.duration)
        
        if args.report_file:
            report_file = args.report_file
        else:
            report_file = config.paths.logs_dir / f"performance_report_{int(time.time())}.json"
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 输出报告摘要
        print("\n" + "="*60)
        print("性能报告摘要")
        print("="*60)
        
        if "error" in report:
            print(f"错误: {report['error']}")
        else:
            print(f"监控时长: {report['duration_hours']} 小时")
            print(f"数据点数量: {report['data_points']}")
            print(f"CPU平均使用率: {report['system_stats']['cpu']['avg_percent']:.1f}%")
            print(f"内存平均使用率: {report['system_stats']['memory']['avg_percent']:.1f}%")
            print(f"磁盘平均使用率: {report['system_stats']['disk']['avg_percent']:.1f}%")
            
            if report["gpu_stats"]:
                print("\nGPU统计:")
                for gpu_name, gpu_stats in report["gpu_stats"].items():
                    print(f"{gpu_name}:")
                    print(f"  显存平均使用率: {gpu_stats['memory_utilization']['avg']:.1f}%")
                    if gpu_stats.get("temperature"):
                        print(f"  平均温度: {gpu_stats['temperature']['avg']:.1f}°C")
            
            if report["performance_analysis"]["bottlenecks"]:
                print("\n检测到的瓶颈:")
                for bottleneck in report["performance_analysis"]["bottlenecks"]:
                    print(f"- {bottleneck}")
            
            if report["performance_analysis"]["recommendations"]:
                print("\n优化建议:")
                for rec in report["performance_analysis"]["recommendations"]:
                    print(f"- {rec}")
            
            print(f"\n效率评分: {report['performance_analysis']['efficiency_score']:.1f}/100")
        
        print("="*60)
        print(f"报告已保存到: {report_file}")

if __name__ == "__main__":
    main()