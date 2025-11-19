"""
双显卡并行处理架构
显卡1: 专注PDF->Markdown转换 (MinerU)
显卡2: 专注Markdown->JSON转换 (LLM)
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Lock
import queue
import threading

try:
    import torch
    HAS_GPU = torch.cuda.is_available() and torch.cuda.device_count() >= 2
except ImportError:
    HAS_GPU = False

from .config import Config
from .pdf_processor import PDFProcessor
from .llm_parser import LLMParser
from .data_importer import DataImporter
from ..utils.memory_manager import memory_manager

logger = logging.getLogger(__name__)

@dataclass
class ProcessingStats:
    """处理统计信息"""
    pdf_processed: int = 0
    pdf_failed: int = 0
    md_parsed: int = 0
    md_failed: int = 0
    json_imported: int = 0
    json_failed: int = 0
    pdf_queue_size: int = 0
    md_queue_size: int = 0
    gpu1_utilization: float = 0.0
    gpu2_utilization: float = 0.0
    memory_usage_gb: float = 0.0

class DualGPUPipeline:
    """双显卡并行处理管道"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        
        # 初始化处理器
        self.pdf_processor_gpu1 = PDFProcessor(self.config)

        # 为LLM解析器配置GPU2设备
        if hasattr(self.config, 'llm'):
            # 创建一个新的配置对象，指定GPU2设备
            import copy
            llm_config = copy.deepcopy(self.config)
            llm_config.llm.device = "cuda:1" if HAS_GPU else None
            try:
                llm_config.llm.ollama_url = os.getenv("OLLAMA_GPU1_URL", "http://127.0.0.1:11435")
            except Exception:
                pass
            self.llm_parser_gpu2 = LLMParser(llm_config)
        else:
            # 对于旧的配置类，直接使用
            self.llm_parser_gpu2 = LLMParser(self.config)

        self.data_importer = DataImporter(self.config)
        
        # 任务队列
        self.pdf_queue = queue.Queue(maxsize=1000)
        self.md_queue = queue.Queue(maxsize=1000)
        self.json_queue = queue.Queue(maxsize=1000)
        
        # 统计信息
        self.stats = ProcessingStats()
        self.stats_lock = Lock()
        
        # 停止标志
        self.stop_event = threading.Event()
        
        # 工作线程
        self.workers = []
        
        # 性能监控
        self.performance_log = []
        
    def get_gpu_memory_info(self, device_id: int = 0) -> Dict[str, float]:
        """获取GPU内存信息"""
        if not HAS_GPU:
            return {"total_gb": 0, "free_gb": 0, "used_gb": 0, "utilization": 0}
        
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(device_id)
            used_bytes = total_bytes - free_bytes
            
            return {
                "total_gb": total_bytes / (1024**3),
                "free_gb": free_bytes / (1024**3),
                "used_gb": used_bytes / (1024**3),
                "utilization": (used_bytes / total_bytes) * 100
            }
        except Exception as e:
            logger.warning(f"获取GPU {device_id} 内存信息失败: {e}")
            return {"total_gb": 0, "free_gb": 0, "used_gb": 0, "utilization": 0}
    
    def update_stats(self, **kwargs):
        """更新统计信息"""
        with self.stats_lock:
            for key, value in kwargs.items():
                if hasattr(self.stats, key):
                    setattr(self.stats, key, value)

            # 更新队列大小
            self.stats.pdf_queue_size = self.pdf_queue.qsize()
            self.stats.md_queue_size = self.md_queue.qsize()

            # 更新GPU利用率
            if HAS_GPU:
                gpu1_info = self.get_gpu_memory_info(0)
                gpu2_info = self.get_gpu_memory_info(1) if torch.cuda.device_count() >= 2 else {"utilization": 0, "used_gb": 0}
                self.stats.gpu1_utilization = gpu1_info["utilization"]
                self.stats.gpu2_utilization = gpu2_info["utilization"]
                self.stats.memory_usage_gb = gpu1_info["used_gb"] + gpu2_info.get("used_gb", 0)

        # 定期优化内存使用
        if self.stats.pdf_processed + self.stats.md_parsed + self.stats.json_imported % 10 == 0:
            memory_manager.optimize_memory()
    
    def log_performance(self):
        """记录性能指标"""
        perf_record = {
            "timestamp": time.time(),
            "stats": {
                "pdf_processed": self.stats.pdf_processed,
                "pdf_failed": self.stats.pdf_failed,
                "md_parsed": self.stats.md_parsed,
                "md_failed": self.stats.md_failed,
                "json_imported": self.stats.json_imported,
                "json_failed": self.stats.json_failed,
                "pdf_queue_size": self.stats.pdf_queue_size,
                "md_queue_size": self.stats.md_queue_size,
                "gpu1_utilization": self.stats.gpu1_utilization,
                "gpu2_utilization": self.stats.gpu2_utilization,
                "memory_usage_gb": self.stats.memory_usage_gb
            }
        }
        self.performance_log.append(perf_record)
        
        # 定期写入性能日志
        if len(self.performance_log) % 10 == 0:
            self.save_performance_log()
    
    def save_performance_log(self):
        """保存性能日志"""
        log_file = self.config.paths.logs_dir / "dual_gpu_performance.jsonl"
        try:
            with open(log_file, "a") as f:
                for record in self.performance_log:
                    f.write(json.dumps(record) + "\n")
            self.performance_log.clear()
        except Exception as e:
            logger.error(f"保存性能日志失败: {e}")
    
    def pdf_processing_worker(self, worker_id: int):
        """PDF处理工作线程 (显卡1)"""
        logger.info(f"PDF处理工作线程 {worker_id} 启动 (GPU-1)")
        
        while not self.stop_event.is_set():
            try:
                # 从队列获取PDF文件
                pdf_file = self.pdf_queue.get(timeout=1)
                if pdf_file is None:  # 结束信号
                    break
                
                logger.info(f"工作线程 {worker_id} 处理PDF: {pdf_file.name}")
                
                # 配置GPU1参数
                if HAS_GPU:
                    try:
                        gpu_count = torch.cuda.device_count()
                        device = f"cuda:{worker_id % max(1, gpu_count)}"
                    except Exception:
                        device = "cuda:0"
                else:
                    device = "cpu"
                output_dir = self.config.paths.output_dir / "markdown"
                
                # 处理PDF
                success = self.pdf_processor_gpu1.process_single_pdf(
                    pdf_file, 
                    output_dir,
                    device=device,
                    fast=self.config.pdf_fast_default,
                    text_only=self.config.pdf_text_only_default
                )
                
                if success:
                    # 将生成的MD文件加入MD队列
                    md_file = output_dir / f"{pdf_file.stem}.md"
                    if md_file.exists():
                        self.md_queue.put(md_file)
                        with self.stats_lock:
                            self.stats.pdf_processed += 1
                        logger.info(f"PDF处理成功: {pdf_file.name} -> {md_file.name}")
                    else:
                        with self.stats_lock:
                            self.stats.pdf_failed += 1
                        logger.error(f"PDF处理成功但未找到MD文件: {pdf_file.name}")
                else:
                    with self.stats_lock:
                        self.stats.pdf_failed += 1
                    logger.error(f"PDF处理失败: {pdf_file.name}")
                
                self.pdf_queue.task_done()
                self.update_stats()
                self.log_performance()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"PDF处理工作线程 {worker_id} 错误: {e}")
                if 'pdf_file' in locals():
                    with self.stats_lock:
                        self.stats.pdf_failed += 1
                    self.pdf_queue.task_done()
    
    def md_parsing_worker(self, worker_id: int):
        """MD解析工作线程 (显卡2/CPU)"""
        logger.info(f"MD解析工作线程 {worker_id} 启动")
        
        while not self.stop_event.is_set():
            try:
                # 从队列获取MD文件
                md_file = self.md_queue.get(timeout=1)
                if md_file is None:  # 结束信号
                    break
                
                logger.info(f"工作线程 {worker_id} 解析MD: {md_file.name}")
                
                try:
                    # 解析MD文件
                    json_data = self.llm_parser_gpu2.parse_markdown_file(str(md_file))
                    
                    if json_data and json_data.get("title"):
                        # 将JSON数据加入JSON队列
                        json_item = {
                            "data": json_data,
                            "source_file": str(md_file),
                            "pdf_name": md_file.stem
                        }
                        self.json_queue.put(json_item)
                        with self.stats_lock:
                            self.stats.md_parsed += 1
                        logger.info(f"MD解析成功: {md_file.name}")
                    else:
                        with self.stats_lock:
                            self.stats.md_failed += 1
                        logger.warning(f"MD解析结果不完整: {md_file.name}")
                        
                except Exception as e:
                    with self.stats_lock:
                        self.stats.md_failed += 1
                    logger.error(f"MD解析失败 {md_file.name}: {e}")
                
                self.md_queue.task_done()
                self.update_stats()
                self.log_performance()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"MD解析工作线程 {worker_id} 错误: {e}")
                if 'md_file' in locals():
                    with self.stats_lock:
                        self.stats.md_failed += 1
                    self.md_queue.task_done()
    
    def json_import_worker(self, worker_id: int):
        """JSON入库工作线程"""
        logger.info(f"JSON入库工作线程 {worker_id} 启动")
        
        batch_size = 50
        batch = []
        
        while not self.stop_event.is_set():
            try:
                # 从队列获取JSON数据
                json_item = self.json_queue.get(timeout=1)
                if json_item is None:  # 结束信号
                    if batch:  # 处理剩余数据
                        self._import_batch(batch)
                    break
                
                batch.append(json_item)
                self.json_queue.task_done()
                
                # 批量入库
                if len(batch) >= batch_size:
                    self._import_batch(batch)
                    batch = []
                
                self.update_stats()
                self.log_performance()
                
            except queue.Empty:
                if batch:  # 处理剩余数据
                    self._import_batch(batch)
                    batch = []
                continue
            except Exception as e:
                logger.error(f"JSON入库工作线程 {worker_id} 错误: {e}")
                if 'json_item' in locals():
                    with self.stats_lock:
                        self.stats.json_failed += 1
                    self.json_queue.task_done()
    
    def _import_batch(self, batch: List[Dict]):
        """批量导入JSON数据"""
        try:
            # 提取需要导入的数据
            md_files = [item["source_file"] for item in batch]
            
            # 使用data_importer批量导入
            results = self.data_importer.import_batch(md_files)
            
            with self.stats_lock:
                self.stats.json_imported += results.get("imported", 0)
                self.stats.json_failed += results.get("failed", 0)
            
            logger.info(f"批量导入完成: 成功 {results.get('imported', 0)}, 失败 {results.get('failed', 0)}")
            
        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            with self.stats_lock:
                self.stats.json_failed += len(batch)
    
    def scan_pdf_files(self, input_dir: Path, limit: Optional[int] = None) -> List[Path]:
        """扫描PDF文件"""
        pdf_files = list(input_dir.rglob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]
        
        # 过滤已处理的文件
        output_dir = self.config.paths.output_dir / "markdown"
        filtered_files = []
        for pdf_file in pdf_files:
            md_file = output_dir / f"{pdf_file.stem}.md"
            if not md_file.exists():
                filtered_files.append(pdf_file)
        
        logger.info(f"扫描到 {len(filtered_files)} 个待处理PDF文件")
        return filtered_files
    
    def start_workers(self, num_pdf_workers: int = 2, num_md_workers: int = 4, num_import_workers: int = 2):
        """启动工作线程"""
        logger.info(f"启动工作线程: PDF={num_pdf_workers}, MD={num_md_workers}, Import={num_import_workers}")
        
        # PDF处理工作线程
        for i in range(num_pdf_workers):
            worker = threading.Thread(target=self.pdf_processing_worker, args=(i,))
            worker.start()
            self.workers.append(worker)
        
        # MD解析工作线程
        for i in range(num_md_workers):
            worker = threading.Thread(target=self.md_parsing_worker, args=(i,))
            worker.start()
            self.workers.append(worker)
        
        # JSON入库工作线程
        for i in range(num_import_workers):
            worker = threading.Thread(target=self.json_import_worker, args=(i,))
            worker.start()
            self.workers.append(worker)
    
    def stop_workers(self):
        """停止工作线程"""
        logger.info("停止工作线程...")
        self.stop_event.set()
        
        # 发送结束信号
        for _ in range(len([w for w in self.workers if "pdf" in str(w)])):
            self.pdf_queue.put(None)
        for _ in range(len([w for w in self.workers if "md" in str(w)])):
            self.md_queue.put(None)
        for _ in range(len([w for w in self.workers if "import" in str(w)])):
            self.json_queue.put(None)
        
        # 等待线程结束
        for worker in self.workers:
            worker.join(timeout=30)
        
        logger.info("所有工作线程已停止")
    
    def run_parallel_processing(self, input_dir: Optional[Path] = None, 
                               limit_pdfs: Optional[int] = None,
                               num_pdf_workers: int = 2,
                               num_md_workers: int = 4,
                               num_import_workers: int = 2) -> Dict:
        """运行并行处理"""
        logger.info("=== 开始双显卡并行处理 ===")
        start_time = time.time()
        
        # 扫描PDF文件
        input_path = input_dir or self.config.paths.input_dir
        pdf_files = self.scan_pdf_files(input_path, limit_pdfs)
        
        if not pdf_files:
            logger.warning("未找到待处理的PDF文件")
            return {"success": False, "error": "未找到PDF文件"}
        
        # 启动工作线程
        self.start_workers(num_pdf_workers, num_md_workers, num_import_workers)
        
        # 将PDF文件加入队列
        logger.info(f"将 {len(pdf_files)} 个PDF文件加入处理队列")
        for pdf_file in pdf_files:
            self.pdf_queue.put(pdf_file)
        
        # 等待处理完成
        logger.info("等待处理完成...")
        try:
            # 等待PDF队列处理完成
            while not self.pdf_queue.empty():
                time.sleep(5)
                self.update_stats()
                logger.info(f"处理进度: PDF队列={self.stats.pdf_queue_size}, MD队列={self.stats.md_queue_size}, "
                          f"已处理PDF={self.stats.pdf_processed}, 已解析MD={self.stats.md_parsed}, "
                          f"已入库={self.stats.json_imported}")
            
            # 等待MD队列处理完成
            while not self.md_queue.empty():
                time.sleep(5)
                self.update_stats()
                logger.info(f"等待MD解析完成: MD队列={self.stats.md_queue_size}")
            
            # 等待JSON队列处理完成
            while not self.json_queue.empty():
                time.sleep(5)
                self.update_stats()
                logger.info(f"等待JSON入库完成: JSON队列={self.json_queue.qsize()}")
            
        except KeyboardInterrupt:
            logger.info("用户中断处理")
        
        # 停止工作线程
        self.stop_workers()
        
        # 保存最终性能日志
        self.save_performance_log()
        
        # 计算处理时间
        end_time = time.time()
        total_time = end_time - start_time
        
        results = {
            "success": True,
            "processing_time_seconds": total_time,
            "pdf_processed": self.stats.pdf_processed,
            "pdf_failed": self.stats.pdf_failed,
            "md_parsed": self.stats.md_parsed,
            "md_failed": self.stats.md_failed,
            "json_imported": self.stats.json_imported,
            "json_failed": self.stats.json_failed,
            "throughput_pdf_per_second": self.stats.pdf_processed / total_time if total_time > 0 else 0,
            "final_stats": {
                "gpu1_utilization": self.stats.gpu1_utilization,
                "gpu2_utilization": self.stats.gpu2_utilization,
                "memory_usage_gb": self.stats.memory_usage_gb
            }
        }
        
        logger.info(f"=== 双显卡并行处理完成 ===")
        logger.info(f"处理时间: {total_time:.2f}秒")
        logger.info(f"PDF处理: 成功 {self.stats.pdf_processed}, 失败 {self.stats.pdf_failed}")
        logger.info(f"MD解析: 成功 {self.stats.md_parsed}, 失败 {self.stats.md_failed}")
        logger.info(f"JSON入库: 成功 {self.stats.json_imported}, 失败 {self.stats.json_failed}")
        logger.info(f"整体吞吐: {results['throughput_pdf_per_second']:.2f} PDF/秒")
        
        return results
