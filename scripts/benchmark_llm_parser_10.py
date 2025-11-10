#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用 GPU 30B 本地模型跑 10 篇样本，并记录耗时与字段覆盖率；可选对比基线目录。

示例：
  python scripts/benchmark_llm_parser_10.py \
    --md-dir /root/kb_create/data/output/markdown \
    --out-dir /root/kb_create/data/output/json_gpu_10 \
    --limit 10 \
    --baseline-dir /root/kb_create/data/output/json_quality_check
"""

import sys
import json
import time
from pathlib import Path
import argparse

# 允许相对导入 src/*
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.llm_parser import LLMParser


FIELDS = [
    'title', 'authors', 'abstract', 'keywords', 'year', 'venue', 'doi', 'research_field', 'references'
]


def is_nonempty(field: str, value):
    if field in ('authors', 'keywords', 'references'):
        return isinstance(value, list) and len(value) > 0
    if field == 'year':
        return isinstance(value, int)
    return value is not None and value != ''


def compute_coverage(json_files):
    total = len(json_files)
    cov = {f: 0 for f in FIELDS}
    for fp in json_files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for f in FIELDS:
                if is_nonempty(f, data.get(f)):
                    cov[f] += 1
        except Exception:
            pass
    return {
        f: {
            'count': cov[f],
            'total': total,
            'pct': round((cov[f] / total) * 100, 1) if total else 0.0,
        }
        for f in FIELDS
    }


def parse_and_save(llm: LLMParser, md_file: Path, out_dir: Path):
    t0 = time.time()
    ok = True
    err = ''
    out_path = out_dir / f"{md_file.stem}.json"
    try:
        data = llm.parse_markdown_file(str(md_file))
        if not data or not data.get('title'):
            ok = False
        # pdf_path 仅在正文中明确出现且以 .pdf 结尾时保留
        if data.get('pdf_path') and not str(data['pdf_path']).lower().endswith('.pdf'):
            data['pdf_path'] = None
        if ok:
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        ok = False
        err = str(e)
    elapsed = time.time() - t0
    print(f"{('✅' if ok else '❌')} {md_file.name} elapsed={elapsed:.2f}s {('' if ok else 'err='+err)}")
    return ok, elapsed, str(out_path)


def main():
    ap = argparse.ArgumentParser(description='GPU 30B 解析10篇并对比覆盖率')
    ap.add_argument('--md-dir', type=Path, required=True, help='Markdown目录')
    ap.add_argument('--out-dir', type=Path, required=True, help='输出JSON目录')
    ap.add_argument('--limit', type=int, default=10, help='解析数量')
    ap.add_argument('--baseline-dir', type=Path, help='基线JSON目录（用于覆盖率对比）')
    args = ap.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'benchmark_llm_parser_10.log'
    setup_logging(log_file)

    llm = LLMParser(config)

    if not args.md_dir.exists():
        print(f"❌ 目录不存在: {args.md_dir}")
        return
    md_files = sorted(list(args.md_dir.glob('*.md')))[: args.limit]
    if not md_files:
        print('⚠️ 未找到Markdown文件')
        return

    timings = []
    success_paths = []
    for md in md_files:
        ok, elapsed, outp = parse_and_save(llm, md, args.out_dir)
        timings.append({'file': md.name, 'elapsed_s': elapsed, 'ok': ok, 'out': outp})
        if ok:
            success_paths.append(outp)

    # 写入耗时文件
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.out_dir / 'timings.json', 'w', encoding='utf-8') as f:
        json.dump({'timings': timings}, f, ensure_ascii=False, indent=2)

    # 当前覆盖率
    cov_cur = compute_coverage(success_paths)
    print('\n当前覆盖率:')
    for k, v in cov_cur.items():
        print(f"- {k}: {v['count']}/{v['total']} ({v['pct']}%)")

    # 平均耗时
    avg = round(sum(t['elapsed_s'] for t in timings if t['ok']) / max(1, sum(1 for t in timings if t['ok'])), 2)
    print(f"\n平均耗时(成功样本): {avg}s")

    # 基线覆盖率（可选）
    if args.baseline_dir and args.baseline_dir.exists():
        baseline_files = sorted(list(args.baseline_dir.glob('*.json')))[: len(success_paths)]
        cov_base = compute_coverage(baseline_files)
        print('\n基线覆盖率:')
        for k, v in cov_base.items():
            print(f"- {k}: {v['count']}/{v['total']} ({v['pct']}%)")

        # 简要对比
        print('\n覆盖率对比(当前 - 基线):')
        for k in FIELDS:
            cur = cov_cur[k]['pct']
            base = cov_base[k]['pct']
            diff = round(cur - base, 1)
            sign = '+' if diff >= 0 else ''
            print(f"- {k}: {cur}% vs {base}% ({sign}{diff}%)")


if __name__ == '__main__':
    main()