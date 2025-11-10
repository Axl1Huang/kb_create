#!/usr/bin/env python3
"""
Compare current PostgreSQL schema with the expected schema defined in /root/kb_create/数据库.sql.

- Parses MySQL-style CREATE TABLE statements and extracts column names.
- Fetches actual tables and columns from the 'public' schema.
- Prints a JSON report with table and column differences.

Usage:
  python scripts/compare_schema_with_sql.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config
from core.database import DatabaseManager
from psycopg2.extras import RealDictCursor


def parse_sql_tables(sql_text: str):
    expected = {}
    # Match: CREATE TABLE <name> ( ... ) ENGINE=...
    for m in re.finditer(r"CREATE\s+TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*ENGINE=",
                         sql_text, flags=re.IGNORECASE | re.DOTALL):
        table = m.group(1)
        body = m.group(2)
        cols = []
        for raw in body.splitlines():
            line = raw.strip().rstrip(',')
            if not line or line.startswith('--'):
                continue
            if re.match(r"(?i)^(PRIMARY\s+KEY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN\s+KEY)", line):
                continue
            m2 = re.match(r"`?([A-Za-z_][A-Za-z0-9_]*)`?\s+", line)
            if m2:
                cols.append(m2.group(1))
        expected[table] = cols
    return expected


def fetch_actual_schema(db: DatabaseManager):
    actual = {}
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        )
        tables = cur.fetchall()
        for t in tables:
            name = t['table_name']
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (name,)
            )
            actual[name] = [r['column_name'] for r in cur.fetchall()]
    return actual


def main():
    sql_path = Path('/root/kb_create/数据库.sql')
    if not sql_path.exists():
        print(json.dumps({'error': f'{sql_path} not found'}, ensure_ascii=False))
        sys.exit(1)

    sql_text = sql_path.read_text(encoding='utf-8')
    expected = parse_sql_tables(sql_text)

    config = Config()
    config.setup_directories()
    db = DatabaseManager(config)
    actual = fetch_actual_schema(db)

    expected_tables = sorted(expected.keys())
    actual_tables = sorted(actual.keys())
    missing_tables = [t for t in expected_tables if t not in actual_tables]
    extra_tables = [t for t in actual_tables if t not in expected_tables]

    columns_diff = {}
    for t in expected_tables:
        exp_cols = expected.get(t, [])
        act_cols = actual.get(t, [])
        missing = [c for c in exp_cols if c not in act_cols]
        extra = [c for c in act_cols if c not in exp_cols]
        columns_diff[t] = {'missing': missing, 'extra': extra}

    result = {
        'tables_expected': expected_tables,
        'tables_actual': actual_tables,
        'missing_tables': missing_tables,
        'extra_tables': extra_tables,
        'columns_diff': columns_diff,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()