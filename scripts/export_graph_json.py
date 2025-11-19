#!/usr/bin/env python3
import sys
import json
from pathlib import Path
import argparse
from psycopg2.extras import RealDictCursor

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from core.config import Config
from core.database import DatabaseManager

def fetch_top_fields(db, limit):
    rows = []
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, field_name, frequency
            FROM research_field
            WHERE is_selected = TRUE
            ORDER BY frequency DESC, display_order ASC, field_name ASC
            LIMIT %s
            """,
            (limit,)
        )
        rows = cur.fetchall()
    return rows

def fetch_top_keywords(db, field_id, limit):
    rows = []
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, keyword_name, frequency
            FROM keyword
            WHERE field_id = %s
            ORDER BY frequency DESC, keyword_name ASC
            LIMIT %s
            """,
            (field_id, limit)
        )
        rows = cur.fetchall()
    return rows

def fetch_top_papers_by_keyword(db, keyword_id, limit):
    rows = []
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT p.id, p.title, p.citations_count, p.publication_year
            FROM paper p
            JOIN paper_keyword pk ON pk.paper_id = p.id
            WHERE pk.keyword_id = %s
            ORDER BY p.citations_count DESC NULLS LAST, p.publication_year DESC NULLS LAST, p.title ASC
            LIMIT %s
            """,
            (keyword_id, limit)
        )
        rows = cur.fetchall()
    return rows

def build_graph(db, top_fields, top_keywords, top_papers):
    fields = []
    try:
        frows = fetch_top_fields(db, top_fields)
    except Exception:
        frows = []
    for f in frows:
        try:
            krows = fetch_top_keywords(db, f['id'], top_keywords)
        except Exception:
            krows = []
        keywords = []
        for k in krows:
            try:
                prows = fetch_top_papers_by_keyword(db, k['id'], top_papers)
            except Exception:
                prows = []
            papers = [
                {
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "count": int(r.get("citations_count") or 0)
                }
                for r in prows
            ]
            keywords.append({
                "id": k.get("id"),
                "name": k.get("keyword_name"),
                "count": int(k.get("frequency") or 0),
                "papers": papers
            })
        fields.append({
            "id": f.get("id"),
            "name": f.get("field_name"),
            "count": int(f.get("frequency") or 0),
            "keywords": keywords
        })
    return {"fields": fields}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-fields", type=int, default=20)
    parser.add_argument("--top-keywords", type=int, default=24)
    parser.add_argument("--top-papers", type=int, default=30)
    args = parser.parse_args()

    config = Config()
    config.setup_directories()
    db = DatabaseManager(config)
    graph = build_graph(db, args.top_fields, args.top_keywords, args.top_papers)
    out_dir = config.paths.project_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "graph.json"
    out_path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    print(str(out_path))

if __name__ == "__main__":
    main()
