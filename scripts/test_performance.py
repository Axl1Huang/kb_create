#!/usr/bin/env python3
import sys
import time
import json
import logging
from pathlib import Path
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.dual_gpu_pipeline import DualGPUPipeline

def main():
    parser = argparse.ArgumentParser(description="双显卡性能测试")
    parser.add_argument("--test-pdfs", type=int, default=20, help="测试PDF数量")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    
    args = parser.parse_args()
    
    config = Config()
    config.setup_directories()
    
    log_file = config.paths.logs_dir / "performance_test.log"
    setup_logging(log_file, args.log_level)
    
    print("开始双显卡性能测试...")
    
    # 运行测试
    pipeline = DualGPUPipeline(config)
    
    results = pipeline.run_parallel_processing(
        limit_pdfs=args.test_pdfs,
        num_pdf_workers=4,
        num_md_workers=8,
        num_import_workers=2
    )
    
    print("\n" + "="*60)
    print("性能测试结果")
    print("="*60)
    print(f"处理时间: {results.get('processing_time_seconds', 0):.2f} 秒")
    print(f"PDF处理: 成功 {results.get('pdf_processed', 0)}, 失败 {results.get('pdf_failed', 0)}")
    print(f"MD解析: 成功 {results.get('md_parsed', 0)}, 失败 {results.get('md_failed', 0)}")
    print(f"JSON入库: 成功 {results.get('json_imported', 0)}, 失败 {results.get('json_failed', 0)}")
    print(f"吞吐量: {results.get('throughput_pdf_per_second', 0):.2f} PDF/秒")
    print(f"GPU1利用率: {results.get('final_stats', {}).get('gpu1_utilization', 0):.1f}%")
    print(f"GPU2利用率: {results.get('final_stats', {}).get('gpu2_utilization', 0):.1f}%")
    print("="*60)

if __name__ == "__main__":
    main()