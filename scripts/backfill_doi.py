#!/usr/bin/env python3
import sys
import re
import time
import json
from pathlib import Path
import argparse
import requests
from difflib import SequenceMatcher
from psycopg2.extras import RealDictCursor

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from core.config import Config, setup_logging
from core.database import DatabaseManager

def _clean_title(s: str) -> str:
    if not s:
        return ''
    t = s
    t = re.sub(r"\$[^$]*\$", " ", t)
    t = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", t)
    t = re.sub(r"[{}^]", " ", t)
    t = re.sub(r"\\+", " ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t

def _year_from_crossref(item: dict) -> int:
    y = None
    m = item.get('issued') or {}
    d = m.get('date-parts') or []
    if d and isinstance(d[0], list) and d[0]:
        y = d[0][0]
    return y or 0

def _best_candidate(title: str, venue: str, year: int, items: list) -> dict:
    ct = _clean_title(title)
    cv = (venue or '').strip().lower()
    best = None
    best_score = 0.0
    for it in items:
        api_title = (it.get('title') or [''])[0]
        api_ct = _clean_title(api_title)
        ts = SequenceMatcher(None, ct, api_ct).ratio()
        ys = 1.0
        ay = _year_from_crossref(it)
        if year and ay:
            ys = 1.0 if abs(ay - year) <= 1 else 0.0
        vs = 1.0
        cont = (it.get('container-title') or [''])[0].strip().lower()
        if cv and cont:
            vs = SequenceMatcher(None, cv, cont).ratio()
        score = ts * 0.7 + ys * 0.2 + vs * 0.1
        if ts >= 0.92 and ys > 0 and (not cv or vs >= 0.85):
            if score > best_score:
                best = it
                best_score = score
    return best

def query_crossref(title: str, venue: str, year: int, ua: str, timeout: float) -> dict:
    params = {
        'query.title': title,
        'rows': 5,
        'select': 'DOI,title,author,container-title,issued'
    }
    if venue:
        params['query.container-title'] = venue
    if year:
        params['filter'] = f'from-pub-date:{year}-01-01,until-pub-date:{year}-12-31'
    headers = {'User-Agent': ua}
    r = requests.get('https://api.crossref.org/works', params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json().get('message', {})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--ua', type=str, default='kb_create/doi_backfill (mailto:dev@example.com)')
    parser.add_argument('--rate', type=float, default=0.5)
    parser.add_argument('--timeout', type=float, default=6.0)
    args = parser.parse_args()

    cfg = Config()
    cfg.setup_directories()
    logger = setup_logging(cfg.paths.logs_dir / 'doi_backfill.log')
    db = DatabaseManager(cfg)

    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT p.id, p.title, p.publication_year AS year, v.venue_name AS venue
            FROM paper p
            LEFT JOIN venue v ON v.id = p.venue_id
            WHERE p.doi IS NULL OR TRIM(p.doi) = ''
            ORDER BY p.created_at DESC NULLS LAST
            LIMIT %s
            """,
            (args.limit,)
        )
        rows = cur.fetchall()

    total = len(rows)
    matched = 0
    written = 0
    failures = 0
    samples = []

    for r in rows:
        title = r.get('title') or ''
        venue = r.get('venue') or ''
        year = r.get('year') or 0
        try:
            msg = query_crossref(title, venue, year, args.ua, args.timeout)
            items = msg.get('items') or []
            cand = _best_candidate(title, venue, year, items)
            if cand:
                matched += 1
                doi = cand.get('DOI') or ''
                samples.append({'id': r['id'], 'title': title[:160], 'doi': doi})
                if args.write and doi:
                    with db.get_cursor() as cur:
                        cur.execute("UPDATE paper SET doi = %s WHERE id = %s", (doi, r['id']))
                        written += 1
            else:
                failures += 1
        except Exception as e:
            failures += 1
        time.sleep(max(0.0, args.rate))

    result = {
        'scanned': total,
        'matched': matched,
        'written': written,
        'failed': failures,
        'samples': samples[:20]
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()