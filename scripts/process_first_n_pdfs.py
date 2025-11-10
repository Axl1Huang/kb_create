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
    parser = argparse.ArgumentParser(description="批量将PDF转换为Markdown或文本（默认Markdown）")
    parser.add_argument("--n", type=int, default=3, help="要处理的PDF数量")
    parser.add_argument("--input-dir", type=Path, help="PDF输入目录，默认使用配置中的 input_dir")
    parser.add_argument("--format", choices=["md", "txt"], default="md", help="输出格式：md 或 txt")
    parser.add_argument("--text-only", action="store_true", help="只保留文本，清理图片等非文本文件")
    parser.add_argument("--fast", action="store_true", help="快速模式：关闭公式/表格解析以加速")
    parser.add_argument("--lang", type=str, default=None, help="覆盖默认语言（如 en/ch）")
    parser.add_argument("--method", type=str, default=None, help="覆盖 MinerU 方法（auto/ocr/txt）")
    parser.add_argument("--start", type=int, default=None, help="起始页（0基，包含）")
    parser.add_argument("--end", type=int, default=None, help="结束页（0基，包含）")
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'process_first_n_pdfs.log'
    setup_logging(log_file)

    input_dir = args.input_dir if args.input_dir else config.paths.input_dir
    subdir = 'text' if args.format == 'txt' else 'markdown'
    output_dir = config.paths.output_dir / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    processor = PDFProcessor(config)
    pdfs = list(input_dir.rglob("*.pdf"))[: max(args.n, 0)]
    if not pdfs:
        print(f"⚠️ 未在目录中找到PDF: {input_dir}")
        return

    print(f"将处理前 {len(pdfs)} 个PDF，输出到: {output_dir}，格式: {args.format}")
    results = {"processed": 0, "failed": 0, "errors": []}
    for pdf in pdfs:
        # 通过 Config 的默认值实现 OCR 与语言控制；此处仅允许覆盖语言
        ok = processor.process_single_pdf(
            pdf,
            output_dir,
            output_format=args.format,
            text_only=args.text_only,
            language=args.lang,
            fast=args.fast,
            start_page=args.start,
            end_page=args.end,
        )
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