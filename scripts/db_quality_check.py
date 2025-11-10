#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库质量检查脚本：
- 统计关键表的行数
- 抽样输出最近 N 条论文的核心字段存在性与关联计数

用法：
  python scripts/db_quality_check.py --limit 3
"""

import sys
from pathlib import Path
import argparse
from psycopg2.extras import RealDictCursor

# 加载项目 src 以便导入核心模块
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.database import DatabaseManager


def main():
    parser = argparse.ArgumentParser(description="数据库质量检查")
    parser.add_argument("--limit", type=int, default=3, help="抽样论文数量")
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'db_quality_check.log'
    setup_logging(log_file)

    db = DatabaseManager(config)

    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        tables = [
            'paper','venue','research_field','author','keyword',
            'paper_author','paper_keyword','paper_citation','paper_metadata'
        ]

        print("=== Row counts ===")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) AS c FROM {t};")
            print(f"{t}:", cur.fetchone()['c'])

        print("\n=== Recent papers ===")
        # 仅选择通用存在的列，避免未知列导致事务中断
        cur.execute(
            """
            SELECT id, title, doi, abstract
            FROM paper
            ORDER BY id DESC
            LIMIT %s;
            """,
            (args.limit,)
        )
        papers = cur.fetchall()

        # 统计关联表记录数
        def count_rel(table: str, paper_id: str) -> int:
            # 某些表可能没有 paper_id 列，先检查再统计
            cur.execute(
                """
                SELECT COUNT(*) AS c
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s AND column_name = 'paper_id'
                """,
                (table,)
            )
            if int(cur.fetchone()['c']) == 0:
                return 0
            cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE paper_id = %s;", (paper_id,))
            return int(cur.fetchone()['c'])

        for p in papers:
            pid = p['id']
            authors = count_rel('paper_author', pid)
            keywords = count_rel('paper_keyword', pid)
            metadata = count_rel('paper_metadata', pid)
            title = (p['title'] or '')[:160]
            print({
                'id': pid,
                'title': title,
            # 某些表结构可能不含 year / venue_id / research_field_id
            # 若需更多字段可在此扩展并做存在性检查
            'doi_present': bool(p['doi']),
            'abstract_present': bool(p['abstract']),
            'author_count': authors,
            'keyword_count': keywords,
                'metadata_count': metadata,
            })


if __name__ == '__main__':
    main()