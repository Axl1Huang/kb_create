import os
import sys
from pathlib import Path
import logging

# 允许从项目根运行：python scripts/run_pdf_batch.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 确保可导入 src 包与其下的 utils
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / 'src'))

from src.core.config import Config, setup_logging
from src.core.pdf_processor import PDFProcessor


def main():
    import argparse
    parser = argparse.ArgumentParser(description="仅运行PDF批处理阶段")
    parser.add_argument("--limit", type=int, default=None, help="仅处理前N个PDF")
    parser.add_argument("--stats-every", type=int, default=5, help="每N个文件写入阶段统计")
    args = parser.parse_args()

    config = Config()
    config.setup_directories()

    # 设置日志到 logs/pdf_batch.log
    log_file = config.paths.logs_dir / "pdf_batch.log"
    logger = setup_logging(log_file, "INFO")
    logger.info("=== 仅PDF批处理启动 ===")
    # 选择输入目录：优先环境指定；若无PDF则回退到 data/input
    input_dir = config.paths.input_dir
    try:
        has_pdf = input_dir.exists() and any(input_dir.rglob('*.pdf'))
    except Exception:
        has_pdf = False
    if not has_pdf:
        fallback = PROJECT_ROOT / 'data' / 'input'
        if fallback.exists() and any(fallback.rglob('*.pdf')):
            input_dir = fallback
    logger.info(f"选定输入目录: {input_dir}")

    output_dir = config.paths.output_dir / "markdown"
    processor = PDFProcessor(config)
    results = processor.process_batch(input_dir, output_dir, limit=args.limit, stats_every=args.stats_every)

    print("\n=== PDF批处理结果 ===")
    print(f"成功: {results['processed']} | 失败: {results['failed']}")
    if results.get("errors"):
        print("失败文件:")
        for e in results["errors"]:
            print(" -", e)


if __name__ == "__main__":
    main()