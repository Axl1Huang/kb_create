#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从现有 JSON 目录 (data/output/json_full_parser) 读取结构化论文数据，
并写入数据库。该脚本不会调用 LLM，仅进行 JSON→DB 入库。

用法：
  python kb_create/scripts/run_json_import.py --limit 100
  python kb_create/scripts/run_json_import.py --dir /path/to/json_dir
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

# 允许导入项目核心模块
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from core.config import Config, setup_logging
from core.data_importer import DataImporter


def fix_schema_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """对常见键名进行轻量修复，避免因字段名不一致导致入库失败。"""
    if not isinstance(d, dict):
        return {}
    out = dict(d)
    # 常见变体归一化
    if 'publication_year' in out and 'year' not in out:
        out['year'] = out.get('publication_year')
    # 兼容 'authors' 为字符串或空
    a = out.get('authors')
    if isinstance(a, str):
        out['authors'] = [a] if a.strip() else []
    if a is None:
        out['authors'] = []
    # 兼容 'keywords'
    k = out.get('keywords')
    if isinstance(k, str):
        out['keywords'] = [k] if k.strip() else []
    if k is None:
        out['keywords'] = []
    # references/pollutants 列表兜底
    for key in ['references', 'pollutants']:
        v = out.get(key)
        if v is None:
            out[key] = []
        elif isinstance(v, str):
            out[key] = [v] if v.strip() else []
    # 兜底必需键
    for key in ['title', 'abstract', 'venue', 'research_field', 'doi', 'pdf_path', 'hrt_conditions', 'cod_removal_efficiency', 'enzyme_activities']:
        out.setdefault(key, None)
    return out


def main():
    parser = argparse.ArgumentParser(description='JSON→DB 入库脚本（不调用LLM）')
    parser.add_argument('--dir', type=str, default='', help='JSON目录；默认读取 config.paths.output_dir/json_full_parser')
    parser.add_argument('--limit', type=int, default=0, help='最多处理的文件数；0表示全部')
    parser.add_argument('--diff-only', action='store_true', help='仅导入数据库中不存在的记录（按doi或title跳过已存在）')
    args = parser.parse_args()

    cfg = Config()
    cfg.setup_directories()
    log_file = cfg.paths.logs_dir / 'import_json_only.log'
    logger = setup_logging(log_file, 'INFO')

    # 解析 JSON 目录
    json_dir = Path(args.dir) if args.dir else (cfg.paths.output_dir / 'json_full_parser')
    if not json_dir.exists():
        print(f"JSON目录不存在: {json_dir}")
        return 2

    json_files: List[Path] = sorted(json_dir.glob('*.json'))
    if not json_files:
        print('未找到JSON文件')
        return 3

    if args.limit and args.limit > 0:
        json_files = json_files[:args.limit]

    importer = DataImporter(cfg)
    ok, fail, skipped = 0, 0, 0
    existing_dois = set()
    existing_titles = set()
    if args.diff_only:
        try:
            rows = importer.db.execute_query("SELECT doi, title FROM paper")
            for r in rows:
                d = r.get('doi')
                t = r.get('title')
                if d:
                    existing_dois.add(d)
                if t:
                    existing_titles.add(t)
            logger.info(f"差集模式启用，现有paper计数: {len(rows)}")
        except Exception as e:
            logger.error(f"读取现有paper失败: {e}")
            print('\n=== JSON 导入结果 ===')
            print('成功: 0')
            print('失败: 0')
            print('错误文件样本:')
            return 1
    errors: List[str] = []
    logger.info(f"开始导入 {len(json_files)} 个JSON样本")
    for fp in json_files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            data = fix_schema_keys(raw)
            if args.diff_only:
                dv = data.get('doi')
                tv = data.get('title')
                if (dv and dv in existing_dois) or (tv and tv in existing_titles):
                    skipped += 1
                    continue
            if importer.import_paper_data(data):
                ok += 1
            else:
                fail += 1
                errors.append(fp.name)
        except Exception as e:
            logger.error(f"导入JSON失败 {fp.name}: {e}")
            fail += 1
            errors.append(fp.name)

    logger.info(f"导入完成: 成功 {ok}, 失败 {fail}")
    print('\n=== JSON 导入结果 ===')
    print(f"成功: {ok}")
    print(f"失败: {fail}")
    if args.diff_only:
        print(f"跳过: {skipped}")
    if errors:
        print('错误文件样本:')
        for e in errors[:10]:
            print(f" - {e}")

    return 0 if ok > 0 else 1


if __name__ == '__main__':
    sys.exit(main())