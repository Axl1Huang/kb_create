#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据导入器
将解析后的JSON数据导入到数据库中
"""

import json
import logging
import uuid
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

# 导入数据库连接器
from database_connector.db_connector import (
    DatabaseConnector, Venue, ResearchField, Keyword, Paper, 
    PaperMetadata, PaperKeyword, Author, PaperAuthor
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/axlhuang/kb_create/logs/data_importer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataImporter:
    """数据导入器类"""
    
    def __init__(self, db_config: Dict[str, Any] = None):
        """初始化数据导入器"""
        self.db = DatabaseConnector(db_config)
        self.field_mapping = {}  # 领域映射缓存
        self.venue_mapping = {}  # 期刊映射缓存
        self.keyword_mapping = {}  # 关键词映射缓存
        self.author_mapping = {}  # 作者映射缓存
    
    def import_data_from_json(self, json_path: str) -> bool:
        """
        从JSON文件导入数据
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            导入是否成功
        """
        try:
            # 连接数据库
            if not self.db.connect():
                logger.error("数据库连接失败")
                return False
            
            # 读取JSON数据
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"开始导入 {len(data)} 条文献数据")
            
            # 导入每条记录
            success_count = 0
            for i, record in enumerate(data):
                logger.info(f"处理进度: {i+1}/{len(data)}")
                if self._import_single_record(record):
                    success_count += 1
            
            logger.info(f"数据导入完成. 成功: {success_count}/{len(data)}")
            
            # 断开数据库连接
            self.db.disconnect()
            return True
            
        except Exception as e:
            logger.error(f"导入数据失败: {str(e)}")
            self.db.disconnect()
            return False
    
    def _import_single_record(self, record: Dict[str, Any]) -> bool:
        """
        导入单条记录
        
        Args:
            record: 单条文献记录
            
        Returns:
            导入是否成功
        """
        try:
            # 1. 处理期刊/会议信息
            venue_id = self._process_venue(record)
            
            # 2. 处理研究领域（这里简化处理，实际应该根据关键词分类）
            field_id = self._process_research_field(record)
            
            # 3. 处理文献信息
            paper_id = self._process_paper(record, venue_id)
            if not paper_id:
                return False
            
            # 4. 处理作者信息
            self._process_authors(record, paper_id)
            
            # 5. 处理关键词信息
            self._process_keywords(record, paper_id, field_id)
            
            # 6. 处理元数据
            self._process_metadata(record, paper_id)
            
            return True
            
        except Exception as e:
            logger.error(f"导入单条记录失败: {str(e)}")
            return False
    
    def _process_venue(self, record: Dict[str, Any]) -> Optional[str]:
        """
        处理期刊/会议信息
        
        Args:
            record: 文献记录
            
        Returns:
            venue_id 或 None
        """
        try:
            journal = record.get('journal')
            if not journal:
                return None
            
            # 生成唯一ID
            venue_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, journal.lower()))
            
            # 检查缓存
            if venue_id in self.venue_mapping:
                return self.venue_mapping[venue_id]
            
            # 创建期刊对象
            venue = Venue(
                id=venue_id,
                venue_name=journal,
                venue_type='journal'
            )
            
            # 插入数据库
            if self.db.insert_venue(venue):
                self.venue_mapping[venue_id] = venue_id
                return venue_id
            else:
                return None
                
        except Exception as e:
            logger.warning(f"处理期刊信息失败: {str(e)}")
            return None
    
    def _process_research_field(self, record: Dict[str, Any]) -> str:
        """
        处理研究领域信息
        
        Args:
            record: 文献记录
            
        Returns:
            field_id
        """
        try:
            # 这里简化处理，实际应该根据关键词或领域分类
            # 我们创建一个默认的水质处理领域
            field_name = "水质处理与净化技术"
            field_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, field_name.lower()))
            
            # 检查缓存
            if field_id in self.field_mapping:
                return self.field_mapping[field_id]
            
            # 创建研究领域对象
            field = ResearchField(
                id=field_id,
                field_name=field_name,
                category="环境工程",
                description="水质处理、净化技术及相关研究领域"
            )
            
            # 插入数据库
            if self.db.insert_research_field(field):
                self.field_mapping[field_id] = field_id
                return field_id
            else:
                return field_id  # 即使插入失败也返回ID
                
        except Exception as e:
            logger.warning(f"处理研究领域失败: {str(e)}")
            # 返回默认领域ID
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, "水质处理与净化技术".lower()))
    
    def _process_paper(self, record: Dict[str, Any], venue_id: Optional[str]) -> Optional[str]:
        """
        处理文献信息
        
        Args:
            record: 文献记录
            venue_id: 期刊ID
            
        Returns:
            paper_id 或 None
        """
        try:
            paper_id = record.get('id')
            if not paper_id:
                return None
            
            # 创建文献对象
            paper = Paper(
                id=paper_id,
                title=record.get('title', ''),
                abstract=record.get('abstract'),
                publication_year=record.get('year'),
                venue_id=venue_id,
                doi=record.get('doi')
            )
            
            # 插入数据库
            if self.db.insert_paper(paper):
                return paper_id
            else:
                return None
                
        except Exception as e:
            logger.error(f"处理文献信息失败: {str(e)}")
            return None
    
    def _process_authors(self, record: Dict[str, Any], paper_id: str) -> bool:
        """
        处理作者信息
        
        Args:
            record: 文献记录
            paper_id: 文献ID
            
        Returns:
            处理是否成功
        """
        try:
            authors = record.get('authors', [])
            if not authors:
                return True
            
            for i, author_info in enumerate(authors):
                # 处理单个作者
                author_name = None
                affiliation = None
                
                if isinstance(author_info, dict):
                    author_name = author_info.get('name')
                    affiliation = author_info.get('affiliation')
                elif isinstance(author_info, str):
                    author_name = author_info
                
                if not author_name:
                    continue
                
                # 生成唯一ID
                author_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, author_name.lower()))
                
                # 检查缓存
                if author_id not in self.author_mapping:
                    # 创建作者对象
                    author = Author(
                        id=author_id,
                        author_name=author_name,
                        affiliation=affiliation
                    )
                    
                    # 插入数据库
                    if self.db.insert_author(author):
                        self.author_mapping[author_id] = author_id
                
                # 创建文献-作者关联
                paper_author = PaperAuthor(
                    paper_id=paper_id,
                    author_id=author_id,
                    author_order=i+1
                )
                
                # 插入关联信息
                self.db.insert_paper_author(paper_author)
            
            return True
            
        except Exception as e:
            logger.warning(f"处理作者信息失败: {str(e)}")
            return False
    
    def _process_keywords(self, record: Dict[str, Any], paper_id: str, field_id: str) -> bool:
        """
        处理关键词信息
        
        Args:
            record: 文献记录
            paper_id: 文献ID
            field_id: 领域ID
            
        Returns:
            处理是否成功
        """
        try:
            keywords = record.get('keywords', [])
            if not keywords:
                return True
            
            for keyword_name in keywords:
                if not keyword_name:
                    continue
                
                # 生成唯一ID
                keyword_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{field_id}:{keyword_name.lower()}"))
                
                # 检查缓存
                if keyword_id not in self.keyword_mapping:
                    # 创建关键词对象
                    keyword = Keyword(
                        id=keyword_id,
                        keyword_name=keyword_name,
                        field_id=field_id
                    )
                    
                    # 插入数据库
                    if self.db.insert_keyword(keyword):
                        self.keyword_mapping[keyword_id] = keyword_id
                
                # 创建文献-关键词关联
                paper_keyword = PaperKeyword(
                    paper_id=paper_id,
                    keyword_id=keyword_id
                )
                
                # 插入关联信息
                self.db.insert_paper_keyword(paper_keyword)
            
            return True
            
        except Exception as e:
            logger.warning(f"处理关键词信息失败: {str(e)}")
            return False
    
    def _process_metadata(self, record: Dict[str, Any], paper_id: str) -> bool:
        """
        处理元数据信息
        
        Args:
            record: 文献记录
            paper_id: 文献ID
            
        Returns:
            处理是否成功
        """
        try:
            # 保存原始记录中的其他字段作为元数据
            exclude_fields = {'id', 'title', 'abstract', 'year', 'journal', 'doi', 'authors', 'keywords'}
            
            for key, value in record.items():
                if key in exclude_fields:
                    continue
                
                if value is None:
                    continue
                
                # 创建元数据对象
                metadata = PaperMetadata(
                    paper_id=paper_id,
                    meta_key=key,
                    meta_value=str(value) if not isinstance(value, str) else value,
                    meta_type=type(value).__name__
                )
                
                # 插入数据库
                self.db.insert_paper_metadata(metadata)
            
            return True
            
        except Exception as e:
            logger.warning(f"处理元数据信息失败: {str(e)}")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据导入器")
    parser.add_argument("-i", "--input", required=True, help="输入JSON文件路径")
    
    args = parser.parse_args()
    
    # 创建日志目录
    Path("/home/axlhuang/kb_create/logs").mkdir(parents=True, exist_ok=True)
    
    # 创建导入器实例
    importer = DataImporter()
    
    # 导入数据
    if importer.import_data_from_json(args.input):
        logger.info("数据导入成功")
    else:
        logger.error("数据导入失败")

if __name__ == "__main__":
    main()