"""
优化的数据库管理器
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
import uuid
import logging
from threading import Lock
from .config import UnifiedConfig
from ..exceptions.database_error import DatabaseError

logger = logging.getLogger(__name__)


class OptimizedDatabaseManager:
    """优化的数据库管理器，支持连接池、批量操作和更好的错误处理"""

    _connection_pool = None
    _pool_lock = Lock()

    def __init__(self, config: UnifiedConfig):
        """
        初始化数据库管理器

        Args:
            config: 统一配置对象
        """
        self.config = config.db
        self._initialize_connection_pool()

    def _initialize_connection_pool(self) -> None:
        """初始化连接池"""
        with self._pool_lock:
            if self._connection_pool is None:
                try:
                    self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=2,
                        maxconn=20,
                        host=self.config.host,
                        port=self.config.port,
                        user=self.config.user,
                        password=self.config.password,
                        database=self.config.database,
                        sslmode=getattr(self.config, 'sslmode', 'prefer')
                    )
                    logger.info("数据库连接池初始化成功")
                except Exception as e:
                    logger.error(f"数据库连接池初始化失败: {e}")
                    raise DatabaseError(f"无法初始化数据库连接池: {e}")

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = self._connection_pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(f"数据库连接错误: {e}")
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """获取游标的上下文管理器"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"数据库操作失败: {e}")
                raise DatabaseError(f"数据库操作失败: {e}", str(e))
            finally:
                cursor.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """
        执行查询并返回结果

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        try:
            with self.get_cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            logger.error(f"查询语句: {query}")
            logger.error(f"查询参数: {params}")
            raise DatabaseError(f"查询执行失败: {e}", query, params)

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        执行更新操作，返回影响的行数

        Args:
            query: SQL更新语句
            params: 更新参数

        Returns:
            影响的行数
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                rowcount = cursor.rowcount
                logger.debug(f"更新操作影响行数: {rowcount}")
                return rowcount
        except Exception as e:
            logger.error(f"更新执行失败: {e}")
            logger.error(f"更新语句: {query}")
            logger.error(f"更新参数: {params}")
            raise DatabaseError(f"更新执行失败: {e}", query, params)

    def execute_batch_update(self, query: str, params_list: List[tuple]) -> int:
        """
        执行批量更新操作，返回影响的总行数

        Args:
            query: SQL更新语句
            params_list: 参数列表

        Returns:
            影响的总行数
        """
        total_rows = 0
        try:
            with self.get_cursor() as cursor:
                for params in params_list:
                    cursor.execute(query, params)
                    total_rows += cursor.rowcount
                logger.debug(f"批量更新操作总影响行数: {total_rows}")
                return total_rows
        except Exception as e:
            logger.error(f"批量更新执行失败: {e}")
            logger.error(f"更新语句: {query}")
            logger.error(f"参数列表长度: {len(params_list) if params_list else 0}")
            raise DatabaseError(f"批量更新执行失败: {e}", query, params_list[0] if params_list else None)

    def execute_batch_values(self, query: str, params_list: List[tuple]) -> int:
        """
        使用execute_values执行高效的批量插入操作

        Args:
            query: SQL插入语句（需要使用%s作为占位符）
            params_list: 参数列表

        Returns:
            影响的总行数
        """
        try:
            with self.get_cursor() as cursor:
                execute_values(cursor, query, params_list)
                rowcount = cursor.rowcount
                logger.debug(f"批量插入操作影响行数: {rowcount}")
                return rowcount
        except Exception as e:
            logger.error(f"批量插入执行失败: {e}")
            logger.error(f"插入语句: {query}")
            logger.error(f"参数列表长度: {len(params_list) if params_list else 0}")
            raise DatabaseError(f"批量插入执行失败: {e}", query, params_list[0] if params_list else None)

    def insert_and_get_id(self, query: str, params: tuple) -> Optional[str]:
        """
        插入数据并返回ID

        Args:
            query: SQL插入语句
            params: 插入参数

        Returns:
            插入记录的ID
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                if result:
                    # 如果结果是字典格式（使用RealDictCursor）
                    if isinstance(result, dict):
                        return result.get('id', None)
                    # 如果结果是元组格式
                    else:
                        return result[0] if len(result) > 0 else None
                return None
        except Exception as e:
            logger.error(f"插入执行失败: {e}")
            logger.error(f"插入语句: {query}")
            logger.error(f"插入参数: {params}")
            raise DatabaseError(f"插入执行失败: {e}", query, params)

    def get_or_create_id(self, table: str, field: str, value: str,
                        additional_fields: Optional[Dict] = None) -> str:
        """
        获取或创建记录的ID

        Args:
            table: 表名
            field: 字段名
            value: 字段值
            additional_fields: 附加字段

        Returns:
            记录ID
        """
        try:
            # 先检查是否存在（使用正确的字段名）
            db_field = field
            # 表名到字段名的映射
            field_mapping = {
                'author': 'author_name',
                'keyword': 'keyword_name',
                'research_field': 'field_name',
                'venue': 'venue_name'
            }

            if table in field_mapping and field == field_mapping[table]:
                db_field = field_mapping[table]

            query = f"SELECT id FROM {table} WHERE {db_field} = %s"
            result = self.execute_query(query, (value,))

            if result:
                logger.debug(f"从{table}表中找到已存在的记录: {value}")
                return result[0]['id']

            # 不存在则创建
            if additional_fields is None:
                additional_fields = {}

            fields = {field: value, **additional_fields}

            # 根据表名调整字段名和ID长度
            # 表名到ID长度的映射
            id_length_mapping = {
                'author': 100,
                'keyword': 100,
                'research_field': 50,
                'venue': 50
            }

            # 表名到字段过滤的映射
            field_filter_mapping = {
                'author': {'author_name'},
                'keyword': {'keyword_name', 'field_id'},
                'research_field': {'field_name'},
                'venue': {'venue_name', 'venue_type', 'publisher', 'impact_factor'}
            }

            # 过滤字段
            if table in field_filter_mapping:
                allowed_fields = field_filter_mapping[table]
                filtered_fields = {}
                for k, v in fields.items():
                    # 保留允许的字段和非'field'的字段
                    if k in allowed_fields or (k != 'field' and table not in field_filter_mapping):
                        filtered_fields[k] = v
                fields = filtered_fields

            field_names = ', '.join(fields.keys())

            # 生成ID（根据表结构调整长度）
            if table in id_length_mapping:
                record_id = str(uuid.uuid4())[:id_length_mapping[table]]
            else:
                record_id = str(uuid.uuid4())

            fields['id'] = record_id
            # 为VALUES子句生成占位符（不包括id字段，因为id已经在VALUES中有一个%s了）
            value_fields = {k: v for k, v in fields.items() if k != 'id'}
            field_placeholders = ', '.join(['%s'] * len(value_fields))

            insert_query = f"""
                INSERT INTO {table} (id, {field_names})
                VALUES (%s, {field_placeholders})
                RETURNING id
            """

            # 构建参数列表，第一个是record_id，然后是除id外的所有字段值
            field_values = [v for k, v in value_fields.items()]
            params = [record_id] + field_values
            result = self.insert_and_get_id(insert_query, tuple(params))

            logger.debug(f"在{table}表中创建新记录: {value}")
            return result if result else record_id
        except Exception as e:
            logger.error(f"获取或创建ID失败: {e}")
            raise DatabaseError(f"获取或创建ID失败: {e}")

    def close_all_connections(self) -> None:
        """关闭所有数据库连接"""
        with self._pool_lock:
            if self._connection_pool:
                self._connection_pool.closeall()
                self._connection_pool = None
                logger.info("所有数据库连接已关闭")

    def __del__(self):
        """析构函数，确保连接池被正确关闭"""
        try:
            self.close_all_connections()
        except Exception:
            pass  # 忽略析构期间的错误