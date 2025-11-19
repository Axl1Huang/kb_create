#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于 DOI 的论文去重脚本：
- 找出 DOI 重复的 paper 记录；
- 选择一个“主记录”（优先 abstract/title 完整、关联多的）；
- 合并其关联关系（author、keyword、metadata、citation），避免唯一约束冲突；
- 删除重复的次记录。

用法：
  python scripts/dedupe_papers_by_doi.py --dry-run false

注意：
- 本脚本针对 PostgreSQL；唯一约束冲突时，保留主记录关联，删除重复关联行。
- 合并顺序：author -> keyword -> metadata -> citation；最后删除重复 paper。
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.database import DatabaseManager
from psycopg2.extras import RealDictCursor


def fetch_duplicate_dois(cur) -> List[str]:
    cur.execute(
        """
        SELECT doi
        FROM paper
        WHERE doi IS NOT NULL AND doi <> ''
        GROUP BY doi
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        """
    )
    return [r['doi'] for r in cur.fetchall()]


def fetch_papers_by_doi(cur, doi: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT id, title, abstract, venue_id, publication_year
        FROM paper
        WHERE doi = %s
        ORDER BY id ASC
        """,
        (doi,)
    )
    return list(cur.fetchall())


def assoc_counts(cur, paper_id: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for t, col in [
        ('paper_author', 'paper_id'),
        ('paper_keyword', 'paper_id'),
        ('paper_metadata', 'paper_id'),
    ]:
        cur.execute(f"SELECT COUNT(*) AS c FROM {t} WHERE {col} = %s", (paper_id,))
        counts[t] = int(cur.fetchone()['c'])
    # 引用关系同时考虑被引与引用
    cur.execute("SELECT COUNT(*) AS c FROM paper_citation WHERE citing_paper_id = %s", (paper_id,))
    citing = int(cur.fetchone()['c'])
    cur.execute("SELECT COUNT(*) AS c FROM paper_citation WHERE cited_paper_id = %s", (paper_id,))
    cited = int(cur.fetchone()['c'])
    counts['paper_citation_total'] = citing + cited
    return counts


def choose_canonical(cur, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    # 选择规则：
    # 1) abstract 非空优先；
    # 2) 关联总数更多优先；
    # 3) 回退到列表首元素。
    scored = []
    for r in rows:
        counts = assoc_counts(cur, r['id'])
        completeness = 0
        if r.get('abstract'): completeness += 1
        if r.get('title'): completeness += 0.5
        score = completeness + counts['paper_citation_total']*0.2 + counts['paper_metadata']*0.1 + counts['paper_author']*0.1 + counts['paper_keyword']*0.1
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else rows[0]


def merge_author(cur, src_id: str, dst_id: str):
    # 删除将产生唯一冲突的行，再统一更新剩余行指向 dst
    cur.execute(
        """
        DELETE FROM paper_author pa
        USING paper_author pa2
        WHERE pa.paper_id = %s
          AND pa2.paper_id = %s
          AND pa.author_id = pa2.author_id
        """,
        (src_id, dst_id)
    )
    cur.execute("UPDATE paper_author SET paper_id = %s WHERE paper_id = %s", (dst_id, src_id))


def merge_keyword(cur, src_id: str, dst_id: str):
    cur.execute(
        """
        DELETE FROM paper_keyword pk
        USING paper_keyword pk2
        WHERE pk.paper_id = %s
          AND pk2.paper_id = %s
          AND pk.keyword_id = pk2.keyword_id
        """,
        (src_id, dst_id)
    )
    cur.execute("UPDATE paper_keyword SET paper_id = %s WHERE paper_id = %s", (dst_id, src_id))


def merge_metadata(cur, src_id: str, dst_id: str):
    cur.execute(
        """
        DELETE FROM paper_metadata pm
        USING paper_metadata pm2
        WHERE pm.paper_id = %s
          AND pm2.paper_id = %s
          AND pm.meta_key = pm2.meta_key
        """,
        (src_id, dst_id)
    )
    cur.execute("UPDATE paper_metadata SET paper_id = %s WHERE paper_id = %s", (dst_id, src_id))


def merge_citation(cur, src_id: str, dst_id: str):
    # 处理引用唯一约束 (citing_paper_id, cited_paper_id)
    # 先删除潜在重复，再更新两方向引用
    cur.execute(
        """
        DELETE FROM paper_citation c
        USING paper_citation c2
        WHERE c.citing_paper_id = %s
          AND c2.citing_paper_id = %s
          AND c.cited_paper_id = c2.cited_paper_id
        """,
        (src_id, dst_id)
    )
    cur.execute(
        """
        DELETE FROM paper_citation c
        USING paper_citation c2
        WHERE c.cited_paper_id = %s
          AND c2.cited_paper_id = %s
          AND c.citing_paper_id = c2.citing_paper_id
        """,
        (src_id, dst_id)
    )
    cur.execute("UPDATE paper_citation SET citing_paper_id = %s WHERE citing_paper_id = %s", (dst_id, src_id))
    cur.execute("UPDATE paper_citation SET cited_paper_id = %s WHERE cited_paper_id = %s", (dst_id, src_id))


def dedupe_group(conn, cur, doi: str, dry_run: bool = False) -> Dict[str, Any]:
    papers = fetch_papers_by_doi(cur, doi)
    if len(papers) <= 1:
        return {'doi': doi, 'duplicates': 0, 'canonical': None}
    canonical = choose_canonical(cur, papers)
    canonical_id = canonical['id']
    removed = 0
    for p in papers:
        pid = p['id']
        if pid == canonical_id:
            continue
        # 合并关联
        merge_author(cur, pid, canonical_id)
        merge_keyword(cur, pid, canonical_id)
        merge_metadata(cur, pid, canonical_id)
        merge_citation(cur, pid, canonical_id)
        # 删除次记录
        cur.execute("DELETE FROM paper WHERE id = %s", (pid,))
        removed += 1
    if dry_run:
        conn.rollback()
    else:
        conn.commit()
    return {'doi': doi, 'duplicates': len(papers)-1, 'canonical': canonical_id, 'removed': removed}


def main():
    parser = argparse.ArgumentParser(description='按 DOI 去重 paper 并合并关联')
    parser.add_argument('--dry-run', type=str, default='false', help='true 则不落库，仅模拟')
    args = parser.parse_args()
    dry = str(args.dry_run).lower() == 'true'

    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'dedupe_papers_by_doi.log'
    setup_logging(log_file)

    db = DatabaseManager(config)
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        dois = fetch_duplicate_dois(cur)
        print(f'发现重复 DOI 组数: {len(dois)}')
        total_removed = 0
        for i, doi in enumerate(dois, start=1):
            try:
                res = dedupe_group(conn, cur, doi, dry_run=dry)
                print(f"[{i}/{len(dois)}] DOI={doi} -> 保留 {res['canonical']}，删除 {res.get('removed', 0)}")
                total_removed += res.get('removed', 0)
            except Exception as e:
                conn.rollback()
                print(f"❌ 处理 DOI={doi} 失败: {e}")
        print(f'完成。总计删除重复记录: {total_removed}')


if __name__ == '__main__':
    main()