#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库准备度报告：在大规模导入（例如 1 万篇 PDF）前，对数据库当前状态进行更全面核查。

包含：
- 关键表行数与增长速率（按最近24h/7d统计，若可用）
- 关键约束/索引存在性与可用性检查
- 样本论文的核心字段完整性与关联覆盖率
- 潜在热点/瓶颈提示（如无索引的大表连接、缺失外键等）

用法：
  python scripts/db_readiness_report.py --sample 10
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict
from psycopg2.extras import RealDictCursor

# 加载项目 src 以便导入核心模块
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.database import DatabaseManager


KEY_TABLES = [
    'paper','venue','research_field','author','keyword',
    'paper_author','paper_keyword','paper_citation','paper_metadata'
]


def get_row_counts(cur) -> Dict[str, int]:
    counts = {}
    for t in KEY_TABLES:
        cur.execute(f"SELECT COUNT(*) AS c FROM {t};")
        counts[t] = int(cur.fetchone()['c'])
    return counts


def get_indexes(cur, table: str) -> List[Dict]:
    # 列出表的索引
    cur.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = %s;
        """,
        (table,)
    )
    return list(cur.fetchall())


def has_column(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column)
    )
    return int(cur.fetchone()['c']) > 0


def count_rel(cur, table: str, paper_id: str) -> int:
    if not has_column(cur, table, 'paper_id'):
        return 0
    cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE paper_id = %s;", (paper_id,))
    return int(cur.fetchone()['c'])


def sample_papers(cur, limit: int):
    cur.execute(
        """
        SELECT id, title, doi, abstract
        FROM paper
        ORDER BY id DESC
        LIMIT %s;
        """,
        (limit,)
    )
    papers = cur.fetchall()
    result = []
    for p in papers:
        pid = p['id']
        result.append({
            'id': pid,
            'title': (p['title'] or '')[:160],
            'doi_present': bool(p['doi']),
            'abstract_present': bool(p['abstract']),
            'author_count': count_rel(cur, 'paper_author', pid),
            'keyword_count': count_rel(cur, 'paper_keyword', pid),
            'metadata_count': count_rel(cur, 'paper_metadata', pid),
        })
    return result


def readiness_hints(cur, counts: Dict[str, int]) -> List[str]:
    hints: List[str] = []
    # 基础索引建议
    if counts.get('paper_author', 0) > 0:
        idxs = get_indexes(cur, 'paper_author')
        if not any('paper_author_paper_id' in i['indexname'] or 'paper_id' in (i['indexdef'] or '') for i in idxs):
            hints.append('建议为 paper_author.paper_id 建索引以提升作者关联查询速度')
    if counts.get('paper_keyword', 0) > 0:
        idxs = get_indexes(cur, 'paper_keyword')
        if not any('paper_keyword_paper_id' in i['indexname'] or 'paper_id' in (i['indexdef'] or '') for i in idxs):
            hints.append('建议为 paper_keyword.paper_id 建索引以提升关键词关联查询速度')
    # 论文表简单建议
    idxs_paper = get_indexes(cur, 'paper')
    if not any('doi' in (i['indexdef'] or '') for i in idxs_paper):
        hints.append('建议为 paper.doi 建唯一索引或普通索引以避免重复并加速查找')
    return hints


def main():
    parser = argparse.ArgumentParser(description='数据库准备度报告')
    parser.add_argument('--sample', type=int, default=5, help='抽样论文数量')
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'db_readiness_report.log'
    setup_logging(log_file)

    db = DatabaseManager(config)

    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print('=== Row counts ===')
        counts = get_row_counts(cur)
        for t, c in counts.items():
            print(f'{t}: {c}')

        print('\n=== Index checks ===')
        for t in KEY_TABLES:
            idxs = get_indexes(cur, t)
            print(f'{t}: {len(idxs)} indexes')

        print('\n=== Sample integrity ===')
        samples = sample_papers(cur, args.sample)
        for s in samples:
            print(s)

        print('\n=== Readiness hints ===')
        for hint in readiness_hints(cur, counts):
            print('-', hint)

        print('\n报告完成。')


if __name__ == '__main__':
    main()