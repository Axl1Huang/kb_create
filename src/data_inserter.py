#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
import json
from pathlib import Path
from typing import Dict, Any, List
from md_parser import MDParser
from db_manager import DatabaseManager

class DataInserter:
    """
    将解析后的数据插入数据库
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.parser = MDParser()
    
    def connect_database(self) -> bool:
        """
        连接数据库
        
        Returns:
            连接是否成功
        """
        return self.db_manager.connect()
    
    def disconnect_database(self):
        """
        断开数据库连接
        """
        self.db_manager.disconnect()
    
    def insert_paper_data(self, paper_info: Dict[str, Any]) -> bool:
        """
        插入单篇文献数据到数据库
        
        Args:
            paper_info: 解析后的文献信息
            
        Returns:
            插入是否成功
        """
        try:
            # 1. 插入期刊/会议信息
            venue_id = self._insert_venue(paper_info)
            
            # 2. 插入文献信息
            paper_id = self._insert_paper(paper_info, venue_id)
            if not paper_id:
                return False
            
            # 3. 插入作者信息
            self._insert_authors(paper_info, paper_id)
            
            # 4. 插入关键词信息
            self._insert_keywords(paper_info, paper_id)
            
            # 5. 插入参考文献信息
            self._insert_references(paper_info, paper_id)
            
            print(f"文献 '{paper_info.get('title', 'Unknown')}' 数据插入成功")
            return True
        except Exception as e:
            print(f"插入文献数据时出错: {e}")
            return False
    
    def _insert_venue(self, paper_info: Dict[str, Any]) -> str:
        """
        插入期刊/会议信息
        
        Args:
            paper_info: 文献信息
            
        Returns:
            venue_id
        """
        venue_name = paper_info.get('venue', '')
        if not venue_name:
            return ''
        
        # 生成唯一的venue_id
        venue_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, venue_name))
        
        venue_data = {
            'id': venue_id,
            'venue_name': venue_name,
            'venue_abbr': '',
            'venue_type': 'journal',  # 默认为期刊
            'issn': '',
            'publisher': '',
            'impact_factor': 0.0,
            'ccf_rank': 'N',
            'core_rank': '',
            'homepage': '',
            'description': ''
        }
        
        # 尝试插入，如果已存在则返回现有ID
        result_id = self.db_manager.insert_venue(venue_data)
        return result_id if result_id else venue_id
    
    def _insert_paper(self, paper_info: Dict[str, Any], venue_id: str) -> str:
        """
        插入文献信息
        
        Args:
            paper_info: 文献信息
            venue_id: 期刊/会议ID
            
        Returns:
            paper_id
        """
        title = paper_info.get('title', '')
        if not title:
            return ''
        
        # 生成唯一的paper_id
        paper_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, title))
        
        paper_data = {
            'id': paper_id,
            'title': title,
            'abstract': paper_info.get('abstract', ''),
            'publication_year': paper_info.get('year', 0),
            'venue_id': venue_id,
            'doi': '',
            'url': '',
            'pdf_url': '',
            'citations_count': 0,
            'download_count': 0,
            'language': 'en',
            'page_start': 0,
            'page_end': 0,
            'volume': '',
            'issue': '',
            'node_size': 30
        }
        
        # 尝试插入，如果已存在则返回现有ID
        result_id = self.db_manager.insert_paper(paper_data)
        return result_id if result_id else paper_id
    
    def _insert_authors(self, paper_info: Dict[str, Any], paper_id: str):
        """
        插入作者信息
        
        Args:
            paper_info: 文献信息
            paper_id: 文献ID
        """
        authors = paper_info.get('authors', [])
        for i, author in enumerate(authors):
            author_name = author.get('name', '')
            if not author_name:
                continue
            
            # 生成唯一的author_id
            author_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, author_name))
            
            author_data = {
                'id': author_id,
                'author_name': author_name,
                'author_name_en': '',
                'affiliation': author.get('affiliation', ''),
                'email': '',
                'orcid': '',
                'homepage': '',
                'h_index': 0,
                'total_citations': 0,
                'research_interests': ''
            }
            
            # 尝试插入作者信息
            self.db_manager.insert_author(author_data)
            
            # 插入文献-作者关联
            self._insert_paper_author(paper_id, author_id, i+1)
    
    def _insert_paper_author(self, paper_id: str, author_id: str, author_order: int):
        """
        插入文献-作者关联信息
        
        Args:
            paper_id: 文献ID
            author_id: 作者ID
            author_order: 作者顺序
        """
        query = """
        INSERT INTO paper_author (paper_id, author_id, author_order, is_corresponding, contribution)
        VALUES (%(paper_id)s, %(author_id)s, %(author_order)s, FALSE, '')
        ON CONFLICT (paper_id, author_id) DO NOTHING
        """
        
        params = {
            'paper_id': paper_id,
            'author_id': author_id,
            'author_order': author_order
        }
        
        self.db_manager.execute_update(query, params)
    
    def _insert_keywords(self, paper_info: Dict[str, Any], paper_id: str):
        """
        插入关键词信息
        
        Args:
            paper_info: 文献信息
            paper_id: 文献ID
        """
        keywords = paper_info.get('keywords', [])
        field_id = self._get_or_create_research_field()
        
        for i, keyword_name in enumerate(keywords):
            if not keyword_name:
                continue
            
            # 生成唯一的keyword_id
            keyword_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, keyword_name))
            
            keyword_data = {
                'id': keyword_id,
                'keyword_name': keyword_name,
                'field_id': field_id,
                'frequency': 0,
                'weight': 1.0,
                'description': '',
                'color': '',
                'node_size': 40
            }
            
            # 尝试插入关键词信息
            self.db_manager.insert_keyword(keyword_data)
            
            # 插入文献-关键词关联
            self._insert_paper_keyword(paper_id, keyword_id, i == 0)
    
    def _get_or_create_research_field(self) -> str:
        """
        获取或创建默认研究领域
        
        Returns:
            研究领域ID
        """
        field_name = "Water Quality"
        field_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, field_name))
        
        field_data = {
            'id': field_id,
            'field_name': field_name,
            'field_code': 'WQ001',
            'frequency': 0,
            'is_selected': True,
            'category': 'Environmental Science',
            'description': 'Water quality research field',
            'icon': '',
            'color': '#1f77b4',
            'node_size': 50,
            'display_order': 0
        }
        
        # 尝试插入研究领域信息
        result_id = self.db_manager.insert_research_field(field_data)
        return result_id if result_id else field_id
    
    def _insert_paper_keyword(self, paper_id: str, keyword_id: str, is_primary: bool):
        """
        插入文献-关键词关联信息
        
        Args:
            paper_id: 文献ID
            keyword_id: 关键词ID
            is_primary: 是否为主要关键词
        """
        query = """
        INSERT INTO paper_keyword (paper_id, keyword_id, is_primary, relevance_score)
        VALUES (%(paper_id)s, %(keyword_id)s, %(is_primary)s, 1.0)
        ON CONFLICT (paper_id, keyword_id) DO NOTHING
        """
        
        params = {
            'paper_id': paper_id,
            'keyword_id': keyword_id,
            'is_primary': is_primary
        }
        
        self.db_manager.execute_update(query, params)
    
    def _insert_references(self, paper_info: Dict[str, Any], paper_id: str):
        """
        插入参考文献信息
        
        Args:
            paper_info: 文献信息
            paper_id: 文献ID
        """
        references = paper_info.get('references', [])
        for reference in references:
            citation = reference.get('citation', '')
            if not citation:
                continue
            
            # 为参考文献生成唯一ID（简化处理）
            ref_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, citation))[:50]
            
            # 在实际应用中，可能需要更复杂的引用解析和匹配逻辑
            # 这里仅作为示例展示如何插入引用关系
            print(f"参考文献处理: {citation[:50]}...")

def main():
    """
    主函数，用于测试数据插入功能
    """
    # 创建数据插入器实例
    inserter = DataInserter()
    
    # 连接数据库
    if not inserter.connect_database():
        print("数据库连接失败")
        return
    
    try:
        # 解析示例文件
        sample_file = Path("/home/axlhuang/kb_create/sample_md/sample_paper.md")
        if sample_file.exists():
            paper_info = inserter.parser.parse_md_file(sample_file)
            
            # 插入数据
            if inserter.insert_paper_data(paper_info):
                print("示例数据插入成功")
            else:
                print("示例数据插入失败")
        else:
            print("示例文件不存在")
    finally:
        # 断开数据库连接
        inserter.disconnect_database()

if __name__ == "__main__":
    main()