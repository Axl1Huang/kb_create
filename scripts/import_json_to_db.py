#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
读取 JSON 文件（LLM 解析结果），并将数据按数据库 schema 插入云数据库。

支持：
- 导入单个 JSON：--json /path/to/file.json
- 导入目录下所有 JSON：--json-dir /path/to/json_dir

示例：
  python scripts/import_json_to_db.py --json-dir /home/axlhuang/kb_create/test_output/json
"""

import sys
import json
from pathlib import Path
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.data_importer import DataImporter


def import_single(importer: DataImporter, json_file: Path) -> bool:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ok = importer.import_paper_data(data)
        print(f"{'✅' if ok else '❌'} 导入: {json_file}")
        return ok
    except Exception as e:
        print(f"❌ 读取/导入失败: {json_file} -> {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="导入JSON到数据库")
    parser.add_argument("--json", type=Path, help="单个JSON文件路径")
    parser.add_argument("--json-dir", type=Path, help="JSON目录路径")
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'import_json_to_db.log'
    setup_logging(log_file)

    importer = DataImporter(config)
    results = {"imported": 0, "failed": 0}

    if args.json:
        ok = import_single(importer, args.json)
        results["imported" if ok else "failed"] += 1
        print(f"汇总: 导入 {results['imported']} 成功, {results['failed']} 失败")
        return

    if args.json_dir:
        if not args.json_dir.exists():
            print(f"❌ 目录不存在: {args.json_dir}")
            return
        json_files = list(args.json_dir.glob("*.json"))
        if not json_files:
            print("⚠️ 未找到JSON文件")
            return
        for jf in json_files:
            ok = import_single(importer, jf)
            results["imported" if ok else "failed"] += 1
        print(f"汇总: 导入 {results['imported']} 成功, {results['failed']} 失败")
        return

    print("⚠️ 请指定 --json 或 --json-dir")


if __name__ == '__main__':
    main()