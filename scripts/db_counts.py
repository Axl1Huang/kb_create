#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统计数据库关键表的记录数量，用于快速验证写入是否正常。

用法：
  python scripts/db_counts.py
"""

import sys
import json
from pathlib import Path
from psycopg2.extras import RealDictCursor

# 加载项目 src 以便导入核心模块
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config
from core.database import DatabaseManager

KEY_TABLES = [
    'paper', 'author', 'keyword', 'research_field', 'venue',
    'paper_author', 'paper_keyword', 'paper_metadata'
]

def main():
    config = Config()
    db = DatabaseManager(config)

    counts = {}
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        for t in KEY_TABLES:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {t};")
            row = cur.fetchone()
            counts[t] = row['cnt']

        # 取各表最近一条插入时间（若有）
        latest = {}
        for t in KEY_TABLES:
            try:
                cur.execute(f"SELECT created_at FROM {t} ORDER BY created_at DESC LIMIT 1;")
                r = cur.fetchone()
                latest[t] = r['created_at'].isoformat() if r and r.get('created_at') else None
            except Exception:
                latest[t] = None

    print(json.dumps({'counts': counts, 'latest_created_at': latest}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()