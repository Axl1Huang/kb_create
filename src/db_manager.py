#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Dict, Any, Optional

class DatabaseManager:
    """
    数据库连接和操作管理类
    """
    
    def __init__(self):
        """
        初始化数据库连接
        """
        # 加载环境变量
        load_dotenv()
        
        # 数据库连接参数
        self.db_params = {
            'host': os.getenv('DB_HOST'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME', 'knowledge_graph')
        }
        
        # 数据库连接
        self.connection = None
        self.cursor = None
    
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            连接是否成功
        """
        try:
            self.connection = psycopg2.connect(**self.db_params)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            print("数据库连接成功")
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False
    
    def disconnect(self):
        """
        关闭数据库连接
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("数据库连接已关闭")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果
        """
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"查询执行失败: {e}")
            return []
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> bool:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            执行是否成功
        """
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"更新执行失败: {e}")
            self.connection.rollback()
            return False
    
    def insert_venue(self, venue_data: Dict[str, Any]) -> Optional[str]:
        """
        插入期刊/会议信息
        
        Args:
            venue_data: 期刊/会议信息字典
            
        Returns:
            插入记录的ID，失败返回None
        """
        query = """
        INSERT INTO venue (
            id, venue_name, venue_abbr, venue_type, issn, publisher, 
            impact_factor, ccf_rank, core_rank, homepage, description
        ) VALUES (
            %(id)s, %(venue_name)s, %(venue_abbr)s, %(venue_type)s, %(issn)s, 
            %(publisher)s, %(impact_factor)s, %(ccf_rank)s, %(core_rank)s, 
            %(homepage)s, %(description)s
        ) ON CONFLICT (id) DO UPDATE SET
            venue_name = EXCLUDED.venue_name,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        try:
            self.cursor.execute(query, venue_data)
            result = self.cursor.fetchone()
            self.connection.commit()
            return result['id'] if result else None
        except Exception as e:
            print(f"插入期刊/会议信息失败: {e}")
            self.connection.rollback()
            return None
    
    def insert_research_field(self, field_data: Dict[str, Any]) -> Optional[str]:
        """
        插入研究领域信息
        
        Args:
            field_data: 研究领域信息字典
            
        Returns:
            插入记录的ID，失败返回None
        """
        query = """
        INSERT INTO research_field (
            id, field_name, field_code, frequency, is_selected, category, 
            description, icon, color, node_size, display_order
        ) VALUES (
            %(id)s, %(field_name)s, %(field_code)s, %(frequency)s, %(is_selected)s, 
            %(category)s, %(description)s, %(icon)s, %(color)s, %(node_size)s, 
            %(display_order)s
        ) ON CONFLICT (field_code) DO UPDATE SET
            field_name = EXCLUDED.field_name,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        try:
            self.cursor.execute(query, field_data)
            result = self.cursor.fetchone()
            self.connection.commit()
            return result['id'] if result else None
        except Exception as e:
            print(f"插入研究领域信息失败: {e}")
            self.connection.rollback()
            return None
    
    def insert_keyword(self, keyword_data: Dict[str, Any]) -> Optional[str]:
        """
        插入关键词信息
        
        Args:
            keyword_data: 关键词信息字典
            
        Returns:
            插入记录的ID，失败返回None
        """
        query = """
        INSERT INTO keyword (
            id, keyword_name, field_id, frequency, weight, description, 
            color, node_size
        ) VALUES (
            %(id)s, %(keyword_name)s, %(field_id)s, %(frequency)s, %(weight)s, 
            %(description)s, %(color)s, %(node_size)s
        ) ON CONFLICT (id) DO UPDATE SET
            keyword_name = EXCLUDED.keyword_name,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        try:
            self.cursor.execute(query, keyword_data)
            result = self.cursor.fetchone()
            self.connection.commit()
            return result['id'] if result else None
        except Exception as e:
            print(f"插入关键词信息失败: {e}")
            self.connection.rollback()
            return None
    
    def insert_paper(self, paper_data: Dict[str, Any]) -> Optional[str]:
        """
        插入文献信息
        
        Args:
            paper_data: 文献信息字典
            
        Returns:
            插入记录的ID，失败返回None
        """
        # 处理文本字段，确保不会超出限制
        for key in ['title', 'abstract']:
            if key in paper_data and paper_data[key]:
                paper_data[key] = paper_data[key][:65535]  # TEXT类型最大长度
        
        query = """
        INSERT INTO paper (
            id, title, abstract, publication_year, venue_id, doi, url, pdf_url,
            citations_count, download_count, language, page_start, page_end,
            volume, issue, node_size
        ) VALUES (
            %(id)s, %(title)s, %(abstract)s, %(publication_year)s, %(venue_id)s, 
            %(doi)s, %(url)s, %(pdf_url)s, %(citations_count)s, %(download_count)s, 
            %(language)s, %(page_start)s, %(page_end)s, %(volume)s, %(issue)s, 
            %(node_size)s
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        try:
            self.cursor.execute(query, paper_data)
            result = self.cursor.fetchone()
            self.connection.commit()
            return result['id'] if result else None
        except Exception as e:
            print(f"插入文献信息失败: {e}")
            self.connection.rollback()
            return None
    
    def insert_author(self, author_data: Dict[str, Any]) -> Optional[str]:
        """
        插入作者信息
        
        Args:
            author_data: 作者信息字典
            
        Returns:
            插入记录的ID，失败返回None
        """
        query = """
        INSERT INTO author (
            id, author_name, author_name_en, affiliation, email, orcid,
            homepage, h_index, total_citations, research_interests
        ) VALUES (
            %(id)s, %(author_name)s, %(author_name_en)s, %(affiliation)s, %(email)s,
            %(orcid)s, %(homepage)s, %(h_index)s, %(total_citations)s, 
            %(research_interests)s
        ) ON CONFLICT (id) DO UPDATE SET
            author_name = EXCLUDED.author_name,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        
        try:
            self.cursor.execute(query, author_data)
            result = self.cursor.fetchone()
            self.connection.commit()
            return result['id'] if result else None
        except Exception as e:
            print(f"插入作者信息失败: {e}")
            self.connection.rollback()
            return None

def main():
    """
    主函数，用于测试数据库连接
    """
    # 创建数据库管理器实例
    db_manager = DatabaseManager()
    
    # 连接数据库
    if db_manager.connect():
        print("数据库模块测试成功")
        # 断开连接
        db_manager.disconnect()
    else:
        print("数据库模块测试失败")

if __name__ == "__main__":
    main()