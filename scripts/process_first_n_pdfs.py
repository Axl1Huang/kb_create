#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
仅执行 MinerU 的 PDF->Markdown 转换，限制数量以便测试。

示例：
  python scripts/process_first_n_pdfs.py --n 3
"""

import sys
from pathlib import Path
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.pdf_processor import PDFProcessor


def main():
    parser = argparse.ArgumentParser(description="处理前N个PDF为Markdown")
    parser.add_argument("--n", type=int, default=3, help="要处理的PDF数量")
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'process_first_n_pdfs.log'
    setup_logging(log_file)

    input_dir = config.paths.input_dir
    output_md_dir = config.paths.output_dir / 'markdown'
    output_md_dir.mkdir(parents=True, exist_ok=True)

    processor = PDFProcessor(config)
    pdfs = list(input_dir.rglob("*.pdf"))[: max(args.n, 0)]
    if not pdfs:
        print(f"⚠️ 未在目录中找到PDF: {input_dir}")
        return

    print(f"将处理前 {len(pdfs)} 个PDF，输出到: {output_md_dir}")
    results = {"processed": 0, "failed": 0, "errors": []}
    for pdf in pdfs:
        ok = processor.process_single_pdf(pdf, output_md_dir)
        if ok:
            results["processed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(str(pdf))

    print(f"PDF处理完成: 成功 {results['processed']}, 失败 {results['failed']}")
    if results["errors"]:
        print("失败文件:")
        for e in results["errors"]:
            print(f" - {e}")


if __name__ == '__main__':
    main()