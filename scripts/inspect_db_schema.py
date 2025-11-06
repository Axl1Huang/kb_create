#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.database import DatabaseManager
from psycopg2.extras import RealDictCursor


def list_tables_and_columns_single_connection(db: DatabaseManager):
    # 使用单连接枚举信息，避免多次连接引起网络/权限问题
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

        table_names = [t['table_name'] for t in tables]
        print("\n=== 数据库表列表（public） ===")
        for name in table_names:
            print(f"- {name}")

        print("\n=== 每个表的字段信息 ===")
        for name in table_names:
            print(f"\n表: {name}")
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (name,)
            )
            cols = cur.fetchall()
            for c in cols:
                print(f"  - {c['column_name']}: {c['data_type']} (nullable={c['is_nullable']})")


def main():
    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'inspect_db_schema.log'
    setup_logging(log_file)

    db = DatabaseManager(config)
    try:
        with db.get_connection() as _:
            print("✅ 成功连接到数据库")
        list_tables_and_columns_single_connection(db)
    except Exception as e:
        print(f"❌ 数据库连接或查询失败: {e}")


if __name__ == '__main__':
    main()