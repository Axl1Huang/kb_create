#!/usr/bin/env python3
"""
高性能双显卡批处理脚本
针对96G内存和120G存储空间优化
支持大规模PDF文件的并行处理
"""

import sys
import time
import json
import logging
import psutil
import gc
from pathlib import Path
from typing import Optional, Dict, List
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.dual_gpu_pipeline import DualGPUPipeline
from src.utils.memory_manager import memory_manager

def get_system_info():
    """获取系统信息"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "total_memory_gb": memory.total / (1024**3),
        "available_memory_gb": memory.available / (1024**3),
        "memory_percent": memory.percent,
        "total_disk_gb": disk.total / (1024**3),
        "free_disk_gb": disk.free / (1024**3),
        "disk_percent": disk.percent,
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=1)
    }

def optimize_memory_settings(system_info: Dict) -> Dict:
    """根据系统配置优化内存设置"""
    total_memory_gb = system_info["total_memory_gb"]
    available_memory_gb = system_info["available_memory_gb"]
    
    # 根据96G内存优化配置
    if total_memory_gb >= 64:
        # 大内存配置
        pdf_batch_size = 100
        md_batch_size = 200
        max_pdf_workers = 4
        max_md_workers = 8
        max_import_workers = 4
        queue_size = 2000
        memory_threshold_gb = 80  # 使用80%内存作为阈值
    elif total_memory_gb >= 32:
        # 中等内存配置
        pdf_batch_size = 50
        md_batch_size = 100
        max_pdf_workers = 2
        max_md_workers = 4
        max_import_workers = 2
        queue_size = 1000
        memory_threshold_gb = 25
    else:
        # 小内存配置
        pdf_batch_size = 20
        md_batch_size = 50
        max_pdf_workers = 1
        max_md_workers = 2
        max_import_workers = 1
        queue_size = 500
        memory_threshold_gb = 8
    
    return {
        "pdf_batch_size": pdf_batch_size,
        "md_batch_size": md_batch_size,
        "max_pdf_workers": max_pdf_workers,
        "max_md_workers": max_md_workers,
        "max_import_workers": max_import_workers,
        "queue_size": queue_size,
        "memory_threshold_gb": memory_threshold_gb,
        "max_memory_usage_gb": min(available_memory_gb * 0.9, memory_threshold_gb)
    }

def monitor_system_resources(log_file: Path, stop_event):
    """监控系统资源"""
    while not stop_event.is_set():
        try:
            system_info = get_system_info()

            # 使用内存管理器检查和优化内存
            memory_manager.optimize_memory(threshold_percent=90)

            # 检查磁盘空间
            if system_info["disk_percent"] > 85:
                logging.warning(f"磁盘空间不足: {system_info['free_disk_gb']:.1f}GB 剩余")

            # 记录系统状态
            with open(log_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": time.time(),
                    "system_info": system_info
                }) + "\n")
            
            time.sleep(30)  # 每30秒检查一次
            
        except Exception as e:
            logging.error(f"系统监控错误: {e}")
            time.sleep(60)

def create_performance_report(results: Dict, system_info: Dict, optimization_settings: Dict, output_file: Path):
    """创建性能报告"""
    report = {
        "timestamp": time.time(),
        "system_info": system_info,
        "optimization_settings": optimization_settings,
        "processing_results": results,
        "performance_metrics": {
            "total_pdfs_processed": results.get("pdf_processed", 0),
            "total_processing_time": results.get("processing_time_seconds", 0),
            "pdf_throughput_per_second": results.get("throughput_pdf_per_second", 0),
            "pdf_throughput_per_hour": results.get("throughput_pdf_per_second", 0) * 3600,
            "memory_efficiency": results.get("pdf_processed", 0) / (optimization_settings["max_memory_usage_gb"] * 1024),
            "gpu_utilization": {
                "gpu1": results.get("final_stats", {}).get("gpu1_utilization", 0),
                "gpu2": results.get("final_stats", {}).get("gpu2_utilization", 0)
            }
        },
        "recommendations": []
    }
    
    # 生成优化建议
    if results.get("throughput_pdf_per_second", 0) < 0.5:
        report["recommendations"].append("PDF处理吞吐量较低，建议增加PDF工作线程数")
    
    if results.get("final_stats", {}).get("gpu1_utilization", 0) < 70:
        report["recommendations"].append("GPU1利用率较低，建议优化MinerU配置")
    
    if results.get("final_stats", {}).get("gpu2_utilization", 0) < 70:
        report["recommendations"].append("GPU2利用率较低，建议优化LLM配置")
    
    if system_info["memory_percent"] > 85:
        report["recommendations"].append("内存使用率较高，建议增加内存或优化批处理大小")
    
    # 保存报告
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

def main():
    parser = argparse.ArgumentParser(description="高性能双显卡批处理脚本")
    parser.add_argument("--input-dir", type=Path, help="PDF输入目录")
    parser.add_argument("--limit", type=int, help="限制处理的PDF数量")
    parser.add_argument("--pdf-workers", type=int, default=None, help="PDF处理工作线程数")
    parser.add_argument("--md-workers", type=int, default=None, help="MD解析工作线程数")
    parser.add_argument("--import-workers", type=int, default=None, help="JSON入库工作线程数")
    parser.add_argument("--memory-limit", type=int, default=None, help="内存使用限制(GB)")
    parser.add_argument("--monitor", action="store_true", help="启用系统监控")
    parser.add_argument("--output-report", type=Path, default=None, help="性能报告输出文件")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    
    args = parser.parse_args()
    
    # 配置日志
    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / "high_performance_batch.log"
    setup_logging(log_file, args.log_level)
    
    logger = logging.getLogger(__name__)
    
    # 获取系统信息
    logger.info("获取系统信息...")
    system_info = get_system_info()
    logger.info(f"系统配置: {json.dumps(system_info, indent=2)}")
    
    # 优化内存设置
    logger.info("优化内存设置...")
    optimization_settings = optimize_memory_settings(system_info)
    logger.info(f"优化配置: {json.dumps(optimization_settings, indent=2)}")
    
    # 检查系统资源
    if system_info["memory_percent"] > 85:
        logger.warning("系统内存使用率较高，可能影响处理性能")
    
    if system_info["disk_percent"] > 90:
        logger.error("磁盘空间不足，请先清理空间")
        return 1
    
    # 启动系统监控
    monitor_thread = None
    if args.monitor:
        monitor_log = config.paths.logs_dir / "system_monitor.jsonl"
        stop_event = threading.Event()
        monitor_thread = threading.Thread(target=monitor_system_resources, args=(monitor_log, stop_event))
        monitor_thread.start()
        logger.info("系统监控已启动")
    
    try:
        # 创建双显卡管道
        logger.info("创建双显卡并行处理管道...")
        pipeline = DualGPUPipeline(config)
        
        # 设置工作线程数
        num_pdf_workers = args.pdf_workers or optimization_settings["max_pdf_workers"]
        num_md_workers = args.md_workers or optimization_settings["max_md_workers"]
        num_import_workers = args.import_workers or optimization_settings["max_import_workers"]
        
        logger.info(f"工作线程配置: PDF={num_pdf_workers}, MD={num_md_workers}, Import={num_import_workers}")
        
        # 运行并行处理
        logger.info("开始并行处理...")
        results = pipeline.run_parallel_processing(
            input_dir=args.input_dir,
            limit_pdfs=args.limit,
            num_pdf_workers=num_pdf_workers,
            num_md_workers=num_md_workers,
            num_import_workers=num_import_workers
        )
        
        # 创建性能报告
        if args.output_report:
            report_file = args.output_report
        else:
            report_file = config.paths.logs_dir / f"performance_report_{int(time.time())}.json"
        
        logger.info(f"创建性能报告: {report_file}")
        report = create_performance_report(results, system_info, optimization_settings, report_file)
        
        # 输出结果摘要
        print("\n" + "="*60)
        print("处理结果摘要")
        print("="*60)
        print(f"处理时间: {results.get('processing_time_seconds', 0):.2f} 秒")
        print(f"PDF处理: 成功 {results.get('pdf_processed', 0)}, 失败 {results.get('pdf_failed', 0)}")
        print(f"MD解析: 成功 {results.get('md_parsed', 0)}, 失败 {results.get('md_failed', 0)}")
        print(f"JSON入库: 成功 {results.get('json_imported', 0)}, 失败 {results.get('json_failed', 0)}")
        print(f"整体吞吐: {results.get('throughput_pdf_per_second', 0):.2f} PDF/秒")
        print(f"GPU1利用率: {results.get('final_stats', {}).get('gpu1_utilization', 0):.1f}%")
        print(f"GPU2利用率: {results.get('final_stats', {}).get('gpu2_utilization', 0):.1f}%")
        print("="*60)
        
        # 输出优化建议
        if report["recommendations"]:
            print("\n优化建议:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"{i}. {rec}")
        
        return 0
        
    except Exception as e:
        logger.error(f"批处理失败: {e}")
        return 1
        
    finally:
        # 停止系统监控
        if monitor_thread:
            stop_event.set()
            monitor_thread.join(timeout=5)
            logger.info("系统监控已停止")

if __name__ == "__main__":
    sys.exit(main())