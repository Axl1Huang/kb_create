#!/usr/bin/env python3
"""
统一的批处理入口
"""
import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
import argparse
import gc

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.config import UnifiedConfig, setup_logging
from src.core.pdf_processor import PDFProcessor
from src.core.llm_parser import LLMParser
from src.core.data_importer import DataImporter
from src.core.database import DatabaseManager

class PerformanceMonitor:
    """性能监控器"""
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()

    def record_metric(self, name, value):
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append({
            "timestamp": time.time(),
            "value": value
        })

    def calculate_throughput(self):
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            # 计算处理的PDF数量（假设这是主要指标）
            pdf_processed = len(self.metrics.get("pdf_processed", []))
            return pdf_processed / elapsed
        return 0

    def get_resource_usage(self):
        import psutil
        process = psutil.Process(os.getpid())
        return {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent()
        }

    def identify_bottlenecks(self):
        # 简单的瓶颈识别逻辑
        bottlenecks = []
        if self.metrics.get("pdf_processing_time"):
            avg_time = sum([m["value"] for m in self.metrics["pdf_processing_time"]]) / len(self.metrics["pdf_processing_time"])
            if avg_time > 60:  # 如果平均处理时间超过60秒
                bottlenecks.append("PDF处理时间过长")

        if self.metrics.get("md_parsing_time"):
            avg_time = sum([m["value"] for m in self.metrics["md_parsing_time"]]) / len(self.metrics["md_parsing_time"])
            if avg_time > 30:  # 如果平均解析时间超过30秒
                bottlenecks.append("MD解析时间过长")

        return bottlenecks

    def generate_report(self):
        """生成性能报告"""
        report = {
            "processing_time": time.time() - self.start_time,
            "throughput": self.calculate_throughput(),
            "resource_usage": self.get_resource_usage(),
            "bottlenecks": self.identify_bottlenecks(),
            "metrics": self.metrics
        }
        return report

class MemoryManagedProcessor:
    """内存管理处理器"""
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.memory_threshold = self.calculate_memory_threshold()

    def calculate_memory_threshold(self):
        """计算内存阈值"""
        import psutil
        total_memory = psutil.virtual_memory().total
        # 设置为总内存的80%
        return total_memory * 0.8

    def memory_usage_exceeds_threshold(self):
        """检查内存使用是否超过阈值"""
        import psutil
        current_memory = psutil.virtual_memory().used
        return current_memory > self.memory_threshold

    def cleanup_unused_resources(self):
        """清理未使用的资源"""
        # 清理缓存
        gc.collect()
        # 可以添加更多清理逻辑

    def process_task(self, task):
        """处理任务"""
        if self.memory_usage_exceeds_threshold():
            self.cleanup_unused_resources()
        return task()

class UnifiedBatchProcessor:
    """统一的批处理器"""
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.pdf_processor = PDFProcessor(config)
        self.llm_parser = LLMParser(config)
        self.data_importer = DataImporter(config)
        self.performance_monitor = PerformanceMonitor()
        self.memory_manager = MemoryManagedProcessor(config)

        # 设置日志
        log_file = config.paths.logs_dir / "unified_batch_processor.log"
        self.logger = setup_logging(log_file, "INFO")

    def process_pdfs(self, limit: Optional[int] = None, workers: Optional[int] = None):
        """处理PDF文件"""
        input_dir = self.config.paths.input_dir
        output_dir = self.config.paths.output_dir / "markdown"

        # 临时修改工作线程数
        original_workers = self.config.parallel.pdf_max_workers
        if workers:
            self.config.parallel.pdf_max_workers = workers

        try:
            self.logger.info(f"开始处理PDF文件，输入目录: {input_dir}")
            results = self.pdf_processor.process_batch(input_dir, output_dir, limit=limit)
            self.logger.info(f"PDF处理完成: {results}")
            return results
        finally:
            # 恢复原始工作线程数
            self.config.parallel.pdf_max_workers = original_workers

    def parse_mds(self, limit: Optional[int] = None):
        """解析MD文件"""
        input_dir = self.config.paths.output_dir / "markdown"

        if not input_dir.exists():
            self.logger.error(f"Markdown目录不存在: {input_dir}")
            return {"parsed": 0, "failed": 0, "errors": []}

        # 获取所有markdown文件
        md_files = list(input_dir.glob("*.md"))
        if limit:
            md_files = md_files[:limit]

        if not md_files:
            self.logger.warning("未找到Markdown文件")
            return {"parsed": 0, "failed": 0, "errors": []}

        results = {"parsed": 0, "failed": 0, "errors": []}

        for md_file in md_files:
            try:
                start_time = time.time()
                parsed_data = self.llm_parser.parse_markdown_file(str(md_file))
                parse_time = time.time() - start_time

                if parsed_data and parsed_data.get("title"):
                    results["parsed"] += 1
                    self.performance_monitor.record_metric("md_parsing_time", parse_time)
                    self.logger.info(f"成功解析MD文件: {md_file.name}")
                else:
                    results["failed"] += 1
                    results["errors"].append(str(md_file))
                    self.logger.warning(f"MD文件解析结果不完整: {md_file.name}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(md_file))
                self.logger.error(f"解析MD文件失败 {md_file.name}: {e}")

        self.logger.info(f"MD解析完成: 成功 {results['parsed']}, 失败 {results['failed']}")
        return results

    def import_data(self, limit: Optional[int] = None):
        """导入数据"""
        input_dir = self.config.paths.output_dir / "markdown"

        if not input_dir.exists():
            self.logger.error(f"Markdown目录不存在: {input_dir}")
            return {"imported": 0, "failed": 0, "errors": []}

        # 获取所有markdown文件
        md_files = list(input_dir.glob("*.md"))
        if limit:
            md_files = md_files[:limit]

        if not md_files:
            self.logger.warning("未找到Markdown文件")
            return {"imported": 0, "failed": 0, "errors": []}

        results = self.data_importer.import_batch(md_files)
        self.logger.info(f"数据导入完成: 成功 {results['imported']}, 失败 {results['failed']}")
        return results

    def run_full_pipeline(self, limit: Optional[int] = None, workers: Optional[int] = None):
        """运行完整管道"""
        self.logger.info("=== 开始完整处理管道 ===")

        final_results = {
            "pdf_processing": None,
            "md_parsing": None,
            "data_import": None,
            "success": True
        }

        try:
            # PDF处理阶段
            pdf_results = self.process_pdfs(limit=limit, workers=workers)
            final_results["pdf_processing"] = pdf_results

            # MD解析阶段
            md_results = self.parse_mds(limit=limit)
            final_results["md_parsing"] = md_results

            # 数据导入阶段
            import_results = self.import_data(limit=limit)
            final_results["data_import"] = import_results

            self.logger.info("=== 完整处理管道完成 ===")
            return final_results

        except Exception as e:
            self.logger.error(f"管道执行失败: {e}")
            final_results["success"] = False
            final_results["error"] = str(e)
            return final_results

    def generate_performance_report(self, output_file: Optional[Path] = None):
        """生成性能报告"""
        report = self.performance_monitor.generate_report()

        if not output_file:
            output_file = self.config.paths.logs_dir / f"performance_report_{int(time.time())}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.logger.info(f"性能报告已生成: {output_file}")
        return report

def main():
    parser = argparse.ArgumentParser(
        description="统一的批处理入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python unified_batch_processor.py                          # 完整处理流程
  python unified_batch_processor.py --mode pdf_only          # 只处理PDF
  python unified_batch_processor.py --mode import_only       # 只导入数据
  python unified_batch_processor.py --log-level DEBUG        # 调试模式运行
        """
    )

    parser.add_argument(
        "--mode",
        choices=["full", "pdf_only", "parse_only", "import_only"],
        default="full",
        help="处理模式（默认: full）"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="设置日志级别（默认: INFO）"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制处理的文件数量"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="设置PDF处理的工作线程数"
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="指定配置文件路径"
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        help="指定输入目录（覆盖配置）"
    )

    parser.add_argument(
        "--output-report",
        type=Path,
        help="指定性能报告输出路径"
    )

    args = parser.parse_args()

    try:
        # 加载配置
        config = UnifiedConfig(config_path=args.config)

        # 如果指定了输入目录，覆盖配置
        if args.input_dir:
            config.paths.input_dir = args.input_dir

        config.setup_directories()

        # 设置日志
        log_file = config.paths.logs_dir / "unified_batch_processor.log"
        logger = setup_logging(log_file, args.log_level)

        logger.info("=" * 50)
        logger.info("统一批处理入口")
        logger.info("=" * 50)

        # 创建处理器
        processor = UnifiedBatchProcessor(config)

        # 运行处理
        if args.mode == "pdf_only":
            results = processor.process_pdfs(limit=args.limit, workers=args.workers)
        elif args.mode == "parse_only":
            results = processor.parse_mds(limit=args.limit)
        elif args.mode == "import_only":
            results = processor.import_data(limit=args.limit)
        else:  # full
            results = processor.run_full_pipeline(limit=args.limit, workers=args.workers)

        # 生成性能报告
        if args.output_report:
            processor.generate_performance_report(args.output_report)
        else:
            processor.generate_performance_report()

        # 输出结果
        print("\n" + "=" * 50)
        print("执行结果:")
        print("=" * 50)

        if results.get('success', True):
            print("✅ 处理成功")
        else:
            print("❌ 处理失败")

        if results.get('pdf_processing'):
            pdf = results['pdf_processing']
            print(f"📄 PDF处理: {pdf.get('processed', 0)} 成功, {pdf.get('failed', 0)} 失败")

        if results.get('md_parsing'):
            md = results['md_parsing']
            print(f"📝 MD解析: {md.get('parsed', 0)} 成功, {md.get('failed', 0)} 失败")

        if results.get('data_import'):
            imp = results['data_import']
            print(f"💾 数据导入: {imp.get('imported', 0)} 成功, {imp.get('failed', 0)} 失败")

        if results.get('error'):
            print(f"❗ 错误: {results['error']}")

        print("=" * 50)

        return 0 if results.get('success', True) else 1

    except KeyboardInterrupt:
        print("\n⚠️  用户中断执行")
        return 130
    except Exception as e:
        print(f"\n❌ 致命错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())