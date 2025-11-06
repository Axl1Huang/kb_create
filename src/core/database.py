import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import uuid
import logging
from .config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """统一的数据库管理器"""
    
    def __init__(self, config: Config):
        self.config = config.db
        self.connection = None
        
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                sslmode=getattr(self.config, 'sslmode', 'require')
            )
            yield conn
        finally:
            if conn:
                conn.close()
    
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
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """执行查询并返回结果"""
        with self.get_cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """执行更新操作，返回影响的行数"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def insert_and_get_id(self, query: str, params: tuple) -> Optional[str]:
        """插入数据并返回ID"""
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
    
    def get_or_create_id(self, table: str, field: str, value: str, 
                        additional_fields: Optional[Dict] = None) -> str:
        """获取或创建记录的ID"""
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
        
        return result if result else record_id