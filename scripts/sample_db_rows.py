#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
采样数据库中各关键表的少量记录，便于直观了解当前数据形态。

用法：
  python scripts/sample_db_rows.py --limit 3
"""

import sys
import json
import argparse
import datetime
import decimal
from pathlib import Path
from psycopg2.extras import RealDictCursor

# 加载项目 src 以便导入核心模块
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config
from core.database import DatabaseManager


KEY_TABLES = [
    'paper', 'author', 'keyword', 'research_field', 'venue',
    'paper_author', 'paper_keyword', 'paper_metadata', 'paper_citation', 'user_selection'
]


def truncate_values(row: dict, max_len: int = 160) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, str) and len(v) > max_len:
            out[k] = v[:max_len] + '...'
        else:
            out[k] = v
    return out


def sample_table(cur, table: str, limit: int):
    try:
        cur.execute(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT %s;", (limit,))
        rows = [truncate_values(r) for r in cur.fetchall()]
        return rows
    except Exception:
        # 回退不排序查询
        cur.execute(f"SELECT * FROM {table} LIMIT %s;", (limit,))
        rows = [truncate_values(r) for r in cur.fetchall()]
        return rows


def main():
    parser = argparse.ArgumentParser(description='采样数据库关键表记录')
    parser.add_argument('--limit', type=int, default=3, help='每表采样数量')
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    db = DatabaseManager(config)

    result = {}
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        for t in KEY_TABLES:
            try:
                result[t] = sample_table(cur, t, args.limit)
            except Exception as e:
                result[t] = {'error': str(e)}

    def json_default(o):
        if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return str(o)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=json_default))


if __name__ == '__main__':
    main()