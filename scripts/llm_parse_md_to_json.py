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
  python scripts/llm_parse_md_to_json.py --md-dir /Downloads \
    --out-dir /home/axlhuang/kb_create/data/output/json_full_parser --limit 10
"""

import sys
import json
import argparse
import os
import re
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.llm_parser import LLMParser


DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[A-Za-z0-9][A-Za-z0-9._;()/:\-]+$")


def clean_and_validate_doi(doi: Optional[str]) -> Optional[str]:
    """Return a cleaned, valid DOI or None.

    Rules:
    - Trim whitespace and trailing period.
    - Must start with '10.' + 4-9 digits + '/' + at least 2 chars after '/'.
    - Disallow extremely short suffixes like '10.1016/j'.
    """
    if not doi:
        return None
    s = str(doi).strip().rstrip('.')
    # Quickly reject very short DOIs
    if len(s) < 12:
        return None
    # Require at least 2 characters after '/'
    parts = s.split('/', 1)
    if len(parts) != 2 or len(parts[1]) < 2:
        return None
    # Regex validate common DOI charset patterns
    if DOI_PATTERN.match(s):
        return s
    return None


def atomic_write_json(out_path: Path, data: dict) -> None:
    """Atomically write JSON to out_path to avoid half-written files.

    Writes to out_path+'.tmp' then os.replace to final path.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + '.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, out_path)


def parse_single(parser: LLMParser, md_file: Path, out_dir: Path) -> bool:
    try:
        data = parser.parse_markdown_file(str(md_file))
        if not data or not data.get('title'):
            print(f"❌ 解析失败或缺少标题: {md_file}")
            return False
        # pdf_path 仅在正文中明确出现且以 .pdf 结尾时保留；不再默认写入源MD路径
        if data.get('pdf_path') and not str(data['pdf_path']).lower().endswith('.pdf'):
            data['pdf_path'] = None
        # 清理与校验 DOI，避免导入阶段触发唯一约束冲突
        data['doi'] = clean_and_validate_doi(data.get('doi'))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{md_file.stem}.json"
        # 原子写入，避免半写入导致的“{”残留
        atomic_write_json(out_path, data)
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