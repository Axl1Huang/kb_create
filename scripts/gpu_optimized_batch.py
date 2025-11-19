#!/usr/bin/env python3
"""
GPU优化的批处理脚本
专门针对双显卡环境设计，最大化GPU利用率
"""

import sys
import os
import time
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
import argparse
import threading
import queue

try:
    import torch
    HAS_GPU = torch.cuda.is_available()
    GPU_COUNT = torch.cuda.device_count()
except ImportError:
    HAS_GPU = False
    GPU_COUNT = 0

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.pdf_processor import PDFProcessor
from core.llm_parser import LLMParser
from core.data_importer import DataImporter

def setup_gpu_optimization():
    """设置GPU优化参数"""
    if HAS_GPU:
        # 设置CUDA环境变量
        os.environ["CUDA_LAUNCH_BLOCKING"] = "0"
        os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
        
        # 优化内存分配
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512,garbage_collection_threshold:0.6"
        
        # 清理GPU内存
        for i in range(GPU_COUNT):
            torch.cuda.set_device(i)
            torch.cuda.empty_cache()

def get_gpu_status() -> Dict:
    """获取GPU状态"""
    if not HAS_GPU:
        return {}
    
    status = {}
    for i in range(GPU_COUNT):
        try:
            props = torch.cuda.get_device_properties(i)
            free_bytes, total_bytes = torch.cuda.mem_get_info(i)
            
            status[f"gpu_{i}"] = {
                "name": props.name,
                "total_memory_gb": total_bytes / (1024**3),
                "free_memory_gb": free_bytes / (1024**3),
                "used_memory_gb": (total_bytes - free_bytes) / (1024**3),
                "memory_utilization_percent": ((total_bytes - free_bytes) / total_bytes) * 100
            }
        except Exception as e:
            status[f"gpu_{i}"] = {"error": str(e)}
    
    return status

def process_batch_optimized(input_dir: Path, output_dir: Path, 
                           limit: Optional[int] = None,
                           num_pdf_workers: int = 4,
                           num_md_workers: int = 8) -> Dict:
    """优化的批处理"""
    
    config = Config()
    config.setup_directories()
    
    # 设置GPU优化
    setup_gpu_optimization()
    
    # 获取PDF文件列表
    pdf_files = list(input_dir.rglob("*.pdf"))
    if limit:
        pdf_files = pdf_files[:limit]
    
    if not pdf_files:
        return {"error": "未找到PDF文件"}
    
    # 初始化处理器
    pdf_processor = PDFProcessor(config)
    llm_parser = LLMParser(config)
    data_importer = DataImporter(config)
    
    start_time = time.time()
    results = {
        "pdf_processed": 0,
        "pdf_failed": 0,
        "md_parsed": 0,
        "md_failed": 0,
        "json_imported": 0,
        "json_failed": 0,
        "gpu_stats": []
    }
    
    # 阶段1: PDF处理 (多GPU并行)
    logging.info(f"开始PDF处理阶段，共 {len(pdf_files)} 个文件")
    
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_pdf_workers) as executor:
        # 提交PDF处理任务
        futures = []
        for i, pdf_file in enumerate(pdf_files):
            # 轮询分配GPU
            gpu_id = i % GPU_COUNT if GPU_COUNT > 0 else 0
            future = executor.submit(process_pdf_with_gpu, pdf_file, output_dir, config, gpu_id)
            futures.append((future, pdf_file))
        
        # 收集结果
        for future, pdf_file in futures:
            try:
                success = future.result(timeout=600)  # 10分钟超时
                if success:
                    results["pdf_processed"] += 1
                else:
                    results["pdf_failed"] += 1
            except Exception as e:
                logging.error(f"PDF处理异常 {pdf_file.name}: {e}")
                results["pdf_failed"] += 1
    
    # 阶段2: Markdown解析 (CPU并行)
    md_files = list(output_dir.glob("*.md"))
    logging.info(f"开始Markdown解析阶段，共 {len(md_files)} 个文件")
    
    json_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_md_workers) as executor:
        # 提交MD解析任务
        futures = []
        for md_file in md_files:
            future = executor.submit(parse_md_with_timeout, md_file, llm_parser)
            futures.append((future, md_file))
        
        # 收集结果
        for future, md_file in futures:
            try:
                result = future.result(timeout=600)  # 10分钟超时
                if result:
                    json_results.append({
                        "data": result,
                        "source_file": str(md_file),
                        "pdf_name": md_file.stem
                    })
                    results["md_parsed"] += 1
                else:
                    results["md_failed"] += 1
            except Exception as e:
                logging.error(f"MD解析异常 {md_file.name}: {e}")
                results["md_failed"] += 1
    
    # 阶段3: JSON入库 (批量)
    logging.info(f"开始JSON入库阶段，共 {len(json_results)} 个文件")
    
    if json_results:
        # 分批导入，每批50个
        batch_size = 50
        for i in range(0, len(json_results), batch_size):
            batch = json_results[i:i+batch_size]
            md_files_batch = [item["source_file"] for item in batch]
            
            try:
                import_result = data_importer.import_batch(md_files_batch)
                results["json_imported"] += import_result.get("imported", 0)
                results["json_failed"] += import_result.get("failed", 0)
            except Exception as e:
                logging.error(f"批量导入失败: {e}")
                results["json_failed"] += len(batch)
    
    # 获取最终GPU状态
    results["gpu_stats"] = get_gpu_status()
    results["processing_time_seconds"] = time.time() - start_time
    results["throughput_pdf_per_second"] = results["pdf_processed"] / results["processing_time_seconds"] if results["processing_time_seconds"] > 0 else 0
    
    return results

def process_pdf_with_gpu(pdf_file: Path, output_dir: Path, config: Config, gpu_id: int) -> bool:
    """使用指定GPU处理PDF"""
    try:
        if HAS_GPU:
            torch.cuda.set_device(gpu_id)
            torch.cuda.empty_cache()
        
        pdf_processor = PDFProcessor(config)
        device = f"cuda:{gpu_id}" if HAS_GPU else "cpu"
        
        success = pdf_processor.process_single_pdf(
            pdf_file,
            output_dir,
            device=device,
            fast=True,  # 启用快速模式
            text_only=config.pdf_text_only_default
        )
        
        return success
        
    except Exception as e:
        logging.error(f"GPU {gpu_id} 处理PDF失败 {pdf_file.name}: {e}")
        return False
    finally:
        if HAS_GPU:
            torch.cuda.empty_cache()

def parse_md_with_timeout(md_file: Path, llm_parser: LLMParser) -> Optional[Dict]:
    """带超时的解析"""
    try:
        result = llm_parser.parse_markdown_file(str(md_file))
        if result and result.get("title"):
            return result
        return None
    except Exception as e:
        logging.error(f"解析失败 {md_file.name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="GPU优化的批处理脚本")
    parser.add_argument("--input-dir", type=Path, help="PDF输入目录")
    parser.add_argument("--output-dir", type=Path, help="Markdown输出目录")
    parser.add_argument("--limit", type=int, help="限制处理的PDF数量")
    parser.add_argument("--pdf-workers", type=int, default=4, help="PDF处理工作线程数")
    parser.add_argument("--md-workers", type=int, default=8, help="MD解析工作线程数")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--show-gpu-status", action="store_true", help="显示GPU状态")
    
    args = parser.parse_args()
    
    # 配置
    config = Config()
    config.setup_directories()
    
    log_file = config.paths.logs_dir / "gpu_optimized_batch.log"
    setup_logging(log_file, args.log_level)
    
    # 显示GPU状态
    if args.show_gpu_status:
        gpu_status = get_gpu_status()
        print("GPU状态:")
        print(json.dumps(gpu_status, indent=2, ensure_ascii=False))
        return 0
    
    # 设置输入输出目录
    input_dir = args.input_dir or config.paths.input_dir
    output_dir = args.output_dir or (config.paths.output_dir / "markdown")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查GPU可用性
    if not HAS_GPU:
        logging.warning("未检测到GPU，将使用CPU处理")
    elif GPU_COUNT < 2:
        logging.warning(f"只检测到 {GPU_COUNT} 个GPU，建议至少2个GPU")
    else:
        logging.info(f"检测到 {GPU_COUNT} 个GPU，启用多GPU优化")
    
    # 运行优化的批处理
    logging.info("开始GPU优化的批处理...")
    results = process_batch_optimized(
        input_dir=input_dir,
        output_dir=output_dir,
        limit=args.limit,
        num_pdf_workers=args.pdf_workers,
        num_md_workers=args.md_workers
    )
    
    # 输出结果
    print("\n" + "="*60)
    print("GPU优化批处理结果")
    print("="*60)
    print(f"处理时间: {results.get('processing_time_seconds', 0):.2f} 秒")
    print(f"PDF处理: 成功 {results.get('pdf_processed', 0)}, 失败 {results.get('pdf_failed', 0)}")
    print(f"MD解析: 成功 {results.get('md_parsed', 0)}, 失败 {results.get('md_failed', 0)}")
    print(f"JSON入库: 成功 {results.get('json_imported', 0)}, 失败 {results.get('json_failed', 0)}")
    print(f"整体吞吐: {results.get('throughput_pdf_per_second', 0):.2f} PDF/秒")
    
    if results.get("gpu_stats"):
        print("\nGPU状态:")
        for gpu_name, stats in results["gpu_stats"].items():
            if "error" not in stats:
                print(f"{gpu_name}: 内存使用 {stats['memory_utilization_percent']:.1f}%")
    
    print("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())