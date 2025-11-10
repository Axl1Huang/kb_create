#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
比较 /root/kb_create/数据库.sql 中的列类型（MySQL风格）与当前 PostgreSQL 实际列类型。

输出 JSON：
- tables: 涉及的表列表
- type_mismatches: 每个表的列类型差异（期望 vs 实际 + 映射建议）

用法：
  python scripts/compare_types_with_sql.py
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config
from core.database import DatabaseManager
from psycopg2.extras import RealDictCursor


def normalize_mysql_type(type_str: str) -> str:
    t = type_str.strip().lower()
    # 去掉长度与修饰（如 varchar(255), int(11)）
    t = re.sub(r"\(.*?\)", "", t)
    # 去掉 unsigned / zerofill 等修饰
    t = re.sub(r"\b(unsigned|zerofill)\b", "", t)
    return t.strip()


def mysql_to_pg_hint(mysql_type: str) -> str:
    mt = normalize_mysql_type(mysql_type)
    mapping = {
        'varchar': 'character varying',
        'char': 'character',
        'text': 'text',
        'tinytext': 'text',
        'mediumtext': 'text',
        'longtext': 'text',
        'int': 'integer',
        'integer': 'integer',
        'bigint': 'bigint',
        'smallint': 'smallint',
        'tinyint': 'smallint',  # 或 boolean（tinyint(1) 常用作布尔）
        'float': 'real',
        'double': 'double precision',
        'decimal': 'numeric',
        'datetime': 'timestamp without time zone',
        'timestamp': 'timestamp without time zone',
        'date': 'date',
        'time': 'time without time zone',
        'json': 'jsonb',
        'uuid': 'uuid',
    }
    return mapping.get(mt, mt)


def parse_mysql_columns(sql_text: str) -> Dict[str, Dict[str, str]]:
    """返回 {table: {column: mysql_type_raw}}"""
    result: Dict[str, Dict[str, str]] = {}
    for m in re.finditer(r"CREATE\s+TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*ENGINE=",
                         sql_text, flags=re.IGNORECASE | re.DOTALL):
        table = m.group(1)
        body = m.group(2)
        cols: Dict[str, str] = {}
        for raw in body.splitlines():
            line = raw.strip().rstrip(',')
            if not line or line.startswith('--'):
                continue
            # 跳过约束/索引
            if re.match(r"(?i)^(PRIMARY\s+KEY|UNIQUE|INDEX|KEY|CONSTRAINT|FOREIGN\s+KEY|FULLTEXT)", line):
                continue
            # 提取列名与类型
            m2 = re.match(r"`?([A-Za-z_][A-Za-z0-9_]*)`?\s+([A-Za-z0-9_]+(?:\([^\)]*\))?)", line)
            if m2:
                col = m2.group(1)
                typ = m2.group(2)
                cols[col] = typ
        result[table] = cols
    return result


def fetch_pg_types(db: DatabaseManager) -> Dict[str, Dict[str, Tuple[str, int]]]:
    """返回 {table: {column: (data_type, char_len)}}"""
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
        tables = [r['table_name'] for r in cur.fetchall()]
        for t in tables:
            cur.execute(
                """
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (t,)
            )
            actual[t] = {r['column_name']: (r['data_type'], r['character_maximum_length'] or 0)
                         for r in cur.fetchall()}
    return actual


def main():
    sql_path = Path('/root/kb_create/数据库.sql')
    if not sql_path.exists():
        print(json.dumps({'error': f'{sql_path} not found'}, ensure_ascii=False))
        sys.exit(1)

    sql_text = sql_path.read_text(encoding='utf-8')
    expected = parse_mysql_columns(sql_text)

    config = Config()
    config.setup_directories()
    db = DatabaseManager(config)
    actual = fetch_pg_types(db)

    tables = sorted(set(expected.keys()) | set(actual.keys()))
    type_mismatches = {}
    for t in tables:
        exp_cols = expected.get(t, {})
        act_cols = actual.get(t, {})
        diffs = {}
        for c, exp_type_raw in exp_cols.items():
            exp_hint = mysql_to_pg_hint(exp_type_raw)
            act_type = act_cols.get(c, (None, 0))[0]
            if act_type is None:
                diffs[c] = {
                    'status': 'missing_in_pg',
                    'expected_mysql': exp_type_raw,
                    'expected_pg_hint': exp_hint,
                }
            else:
                if exp_hint != act_type:
                    diffs[c] = {
                        'status': 'type_mismatch',
                        'expected_mysql': exp_type_raw,
                        'expected_pg_hint': exp_hint,
                        'actual_pg': act_type,
                    }
        # 找到PG中存在但SQL未定义的列
        for c in act_cols.keys():
            if c not in exp_cols:
                diffs[c] = {
                    'status': 'extra_in_pg',
                    'actual_pg': act_cols[c][0],
                }
        if diffs:
            type_mismatches[t] = diffs

    result = {
        'tables': tables,
        'type_mismatches': type_mismatches,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()