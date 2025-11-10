#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR高质量通道生成并与旧版Markdown对比的测试脚本。

功能：
- 选取前N个PDF，使用MinerU的OCR模式生成新的Markdown到独立目录；
- 与旧版Markdown（基线目录）做文本归一化后的差异比较；
- 输出每个文件的字符/行统计与相似度，并保存统一diff结果。

示例：
  python scripts/ocr_compare_test.py --n 3 \
    --baseline-dir data/output/markdown \
    --output-dir data/output/markdown_ocr

可选：
- 使用 --lang 指定语言（默认沿用配置）；
- 使用 --start/--end 指定页码范围（0基，包含）；
"""

import sys
from pathlib import Path
import argparse
import difflib

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.pdf_processor import PDFProcessor


def main():
    parser = argparse.ArgumentParser(description="OCR高质量生成并与旧版Markdown对比")
    parser.add_argument("--n", type=int, default=3, help="要处理的PDF数量（从输入目录前N个）")
    parser.add_argument("--input-dir", type=Path, help="PDF输入目录，默认使用配置中的 input_dir")
    parser.add_argument("--baseline-dir", type=Path, help="旧版Markdown目录，默认 data/output/markdown")
    parser.add_argument("--output-dir", type=Path, help="OCR新版Markdown输出目录，默认 data/output/markdown_ocr")
    parser.add_argument("--lang", type=str, default=None, help="覆盖默认语言（如 en/ch）")
    parser.add_argument("--start", type=int, default=None, help="起始页（0基，包含）")
    parser.add_argument("--end", type=int, default=None, help="结束页（0基，包含）")
    parser.add_argument("--fast", action="store_true", help="快速模式：关闭公式/表格解析以加速（为保证质量，建议不加）")
    parser.add_argument("--diff-dir", type=Path, help="diff输出目录，默认 data/output/markdown_ocr_diffs")
    args = parser.parse_args()

    # 加载配置与日志
    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'ocr_compare_test.log'
    setup_logging(log_file)

    # 强制使用OCR方法（不改全局env，仅在本次运行覆盖）
    config.mineru_method = (config.mineru_method or 'auto')
    config.mineru_method = 'ocr'  # 高质量OCR

    # 目录设置
    input_dir = args.input_dir if args.input_dir else config.paths.input_dir
    baseline_dir = args.baseline_dir if args.baseline_dir else (config.paths.output_dir / 'markdown')
    ocr_output_dir = args.output_dir if args.output_dir else (config.paths.output_dir / 'markdown_ocr')
    diff_dir = args.diff_dir if args.diff_dir else (config.paths.output_dir / 'markdown_ocr_diffs')
    ocr_output_dir.mkdir(parents=True, exist_ok=True)
    diff_dir.mkdir(parents=True, exist_ok=True)

    # 选取PDF列表
    pdfs = list(input_dir.rglob("*.pdf"))[: max(args.n, 0)]
    if not pdfs:
        print(f"⚠️ 未在目录中找到PDF: {input_dir}")
        return

    processor = PDFProcessor(config)

    print(f"将处理前 {len(pdfs)} 个PDF，OCR输出到: {ocr_output_dir}")

    summary = []
    for pdf in pdfs:
        ok = processor.process_single_pdf(
            pdf,
            ocr_output_dir,
            output_format="md",
            text_only=False,
            language=args.lang,
            fast=args.fast,
            start_page=args.start,
            end_page=args.end,
        )
        if not ok:
            summary.append({"file": str(pdf), "status": "failed"})
            print(f"❌ 生成失败: {pdf}")
            continue

        baseline_md = baseline_dir / f"{pdf.stem}.md"
        new_md = ocr_output_dir / f"{pdf.stem}.md"

        if not new_md.exists():
            summary.append({"file": str(pdf), "status": "no_new_md"})
            print(f"⚠️ 未找到新MD: {new_md}")
            continue

        new_text = new_md.read_text(encoding="utf-8", errors="ignore")
        baseline_text = baseline_md.read_text(encoding="utf-8", errors="ignore") if baseline_md.exists() else ""

        # 使用处理器的归一化（去除Markdown格式）
        try:
            new_norm = processor._md_to_txt(new_text)
            base_norm = processor._md_to_txt(baseline_text)
        except Exception:
            new_norm = new_text
            base_norm = baseline_text

        # 统计与相似度
        stats = {
            "pdf": pdf.name,
            "baseline_exists": baseline_md.exists(),
            "baseline_chars": len(base_norm),
            "new_chars": len(new_norm),
            "baseline_lines": len(base_norm.splitlines()),
            "new_lines": len(new_norm.splitlines()),
            "similarity": round(difflib.SequenceMatcher(None, base_norm, new_norm).ratio(), 4)
        }

        # 生成统一diff（基于归一化文本）
        diff_lines = list(difflib.unified_diff(
            base_norm.splitlines(),
            new_norm.splitlines(),
            fromfile=str(baseline_md) if baseline_md.exists() else "<baseline-missing>",
            tofile=str(new_md),
            lineterm=""
        ))

        diff_file = diff_dir / f"{pdf.stem}.diff.txt"
        diff_file.write_text("\n".join(diff_lines), encoding="utf-8")

        # 预览前若干行
        preview = "\n".join(diff_lines[:80])
        summary.append({"file": pdf.name, "status": "ok", **stats, "diff_path": str(diff_file), "preview": preview})

        print(f"✅ 完成: {pdf.name}")
        print(f"- 基线MD: {'存在' if baseline_md.exists() else '缺失'}")
        print(f"- 字符: 基线 {stats['baseline_chars']} / 新版 {stats['new_chars']}")
        print(f"- 行数: 基线 {stats['baseline_lines']} / 新版 {stats['new_lines']}")
        print(f"- 相似度: {stats['similarity']}")
        print(f"- Diff保存: {diff_file}")
        print("- Diff预览(前80行):\n" + preview + "\n")

    # 汇总
    ok_cnt = sum(1 for s in summary if s.get("status") == "ok")
    fail_cnt = sum(1 for s in summary if s.get("status") == "failed")
    print(f"\n=== 测试完成 ===")
    print(f"生成成功: {ok_cnt}, 失败: {fail_cnt}")
    print(f"新版MD目录: {ocr_output_dir}")
    print(f"Diff目录: {diff_dir}")


if __name__ == '__main__':
    main()