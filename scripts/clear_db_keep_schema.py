#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.database import DatabaseManager
from psycopg2.extras import RealDictCursor


TRUNCATE_ORDER = [
    # 先清理关系表（按外键依赖）
    'paper_author',
    'paper_keyword',
    'paper_citation',
    'paper_metadata',
    # 再清理从表
    'author',
    'keyword',
    'venue',
    'research_field',
    # 最后清理主表
    'paper',
]


def clear_data_single_connection(db: DatabaseManager):
    print("即将清空数据但保留结构（TRUNCATE）...")
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        for table in TRUNCATE_ORDER:
            try:
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                print(f"- 清空 {table} 完成")
            except Exception as e:
                print(f"⚠️ 清空 {table} 失败: {e}")
        conn.commit()


def main():
    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'clear_db_keep_schema.log'
    setup_logging(log_file)

    db = DatabaseManager(config)
    try:
        with db.get_connection() as _:
            print("✅ 成功连接到数据库")
        clear_data_single_connection(db)
        print("✅ 清空完成")
    except Exception as e:
        print(f"❌ 操作失败: {e}")


if __name__ == '__main__':
    main()