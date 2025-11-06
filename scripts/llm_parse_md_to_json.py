#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用 LLMParser 将 MinerU 生成的 Markdown 文件解析为 JSON。

支持：
- 解析单个 MD 文件：--md /path/to/file.md
- 批量解析目录中的 MD 文件：--md-dir /path/to/md_dir --limit 20
- 指定输出目录：--out-dir /path/to/output_json_dir

输出的 JSON 字段与数据库导入器期望的结构一致：
- title, authors(list), abstract, keywords(list), year, venue,
  research_field, doi, references(list)

示例：
  python scripts/llm_parse_md_to_json.py --md-dir /home/axlhuang/kb_create/output/markdown \
    --out-dir /home/axlhuang/kb_create/test_output/json --limit 10
"""

import sys
import json
from pathlib import Path
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.llm_parser import LLMParser


def parse_single(parser: LLMParser, md_file: Path, out_dir: Path) -> bool:
    try:
        data = parser.parse_markdown_file(str(md_file))
        if not data or not data.get('title'):
            print(f"❌ 解析失败或缺少标题: {md_file}")
            return False
        # 兼容导入器的可选字段：记录源MD路径，导入器将其作为pdf_url写入
        data.setdefault('pdf_path', str(md_file))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{md_file.stem}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 导出JSON: {out_path}")
        return True
    except Exception as e:
        print(f"❌ 解析异常: {md_file} -> {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="LLM解析MD为JSON")
    parser.add_argument("--md", type=Path, help="单个Markdown文件路径")
    parser.add_argument("--md-dir", type=Path, help="Markdown目录路径")
    parser.add_argument("--out-dir", type=Path, required=True, help="输出JSON目录路径")
    parser.add_argument("--limit", type=int, default=0, help="批量解析的最大数量(0表示不限)")
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'llm_parse_md_to_json.log'
    setup_logging(log_file)

    llm = LLMParser(config)
    out_dir = args.out_dir

    results = {"parsed": 0, "failed": 0}

    # 单文件模式
    if args.md:
        ok = parse_single(llm, args.md, out_dir)
        results["parsed" if ok else "failed"] += 1
        print(f"汇总: 解析 {results['parsed']} 成功, {results['failed']} 失败")
        return

    # 目录批量模式
    if args.md_dir:
        if not args.md_dir.exists():
            print(f"❌ 目录不存在: {args.md_dir}")
            return
        md_files = list(args.md_dir.glob("*.md"))
        if args.limit and args.limit > 0:
            md_files = md_files[:args.limit]
        if not md_files:
            print("⚠️ 未找到Markdown文件")
            return
        for md in md_files:
            ok = parse_single(llm, md, out_dir)
            results["parsed" if ok else "failed"] += 1
        print(f"汇总: 解析 {results['parsed']} 成功, {results['failed']} 失败")
        return

    print("⚠️ 请指定 --md 或 --md-dir")


if __name__ == '__main__':
    main()