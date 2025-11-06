#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库连接和配置模块
提供数据库连接、表结构定义和数据操作功能
"""

import pymysql
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/axlhuang/kb_create/logs/database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'your_password',  # 请根据实际情况修改
    'database': 'knowledge_graph',
    'charset': 'utf8mb4'
}

@dataclass
class Venue:
    """期刊/会议表"""
    id: str
    venue_name: str
    venue_abbr: Optional[str] = None
    venue_type: str = 'journal'
    issn: Optional[str] = None
    publisher: Optional[str] = None
    impact_factor: Optional[float] = None
    ccf_rank: Optional[str] = None
    core_rank: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None

@dataclass
class ResearchField:
    """研究领域表"""
    id: str
    field_name: str
    field_code: Optional[str] = None
    frequency: int = 0
    is_selected: bool = True
    category: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    node_size: int = 50
    display_order: int = 0

@dataclass
class Keyword:
    """关键词表"""
    id: str
    keyword_name: str
    field_id: str
    frequency: int = 0
    weight: float = 1.0
    description: Optional[str] = None
    color: Optional[str] = None
    node_size: int = 40

@dataclass
class Paper:
    """文献表"""
    id: str
    title: str
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    venue_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    citations_count: int = 0
    download_count: int = 0
    language: str = 'en'
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    node_size: int = 30

@dataclass
class PaperMetadata:
    """文献元数据表"""
    paper_id: str
    meta_key: str
    meta_value: Optional[str] = None
    meta_type: Optional[str] = None

@dataclass
class PaperKeyword:
    """文献-关键词映射表"""
    paper_id: str
    keyword_id: str
    is_primary: bool = False
    relevance_score: float = 1.0

@dataclass
class Author:
    """作者表"""
    id: str
    author_name: str
    author_name_en: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None
    homepage: Optional[str] = None
    h_index: int = 0
    total_citations: int = 0
    research_interests: Optional[str] = None

@dataclass
class PaperAuthor:
    """文献-作者关联表"""
    paper_id: str
    author_id: str
    author_order: int
    is_corresponding: bool = False
    contribution: Optional[str] = None

class DatabaseConnector:
    """数据库连接器类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化数据库连接器"""
        self.config = config or DB_CONFIG
        self.connection = None
    
    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return False
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def insert_venue(self, venue: Venue) -> bool:
        """插入期刊/会议信息"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO venue (id, venue_name, venue_abbr, venue_type, issn, publisher, 
                                 impact_factor, ccf_rank, core_rank, homepage, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                venue_name=VALUES(venue_name), venue_abbr=VALUES(venue_abbr), venue_type=VALUES(venue_type),
                issn=VALUES(issn), publisher=VALUES(publisher), impact_factor=VALUES(impact_factor),
                ccf_rank=VALUES(ccf_rank), core_rank=VALUES(core_rank), homepage=VALUES(homepage),
                description=VALUES(description)
                """
                cursor.execute(sql, (
                    venue.id, venue.venue_name, venue.venue_abbr, venue.venue_type,
                    venue.issn, venue.publisher, venue.impact_factor, venue.ccf_rank,
                    venue.core_rank, venue.homepage, venue.description
                ))
            self.connection.commit()
            logger.info(f"插入/更新期刊信息: {venue.venue_name}")
            return True
        except Exception as e:
            logger.error(f"插入期刊信息失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_research_field(self, field: ResearchField) -> bool:
        """插入研究领域信息"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO research_field (id, field_name, field_code, frequency, is_selected,
                                          category, description, icon, color, node_size, display_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                field_name=VALUES(field_name), field_code=VALUES(field_code), frequency=VALUES(frequency),
                is_selected=VALUES(is_selected), category=VALUES(category), description=VALUES(description),
                icon=VALUES(icon), color=VALUES(color), node_size=VALUES(node_size), display_order=VALUES(display_order)
                """
                cursor.execute(sql, (
                    field.id, field.field_name, field.field_code, field.frequency,
                    field.is_selected, field.category, field.description, field.icon,
                    field.color, field.node_size, field.display_order
                ))
            self.connection.commit()
            logger.info(f"插入/更新研究领域: {field.field_name}")
            return True
        except Exception as e:
            logger.error(f"插入研究领域失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_keyword(self, keyword: Keyword) -> bool:
        """插入关键词信息"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO keyword (id, keyword_name, field_id, frequency, weight, description, color, node_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                keyword_name=VALUES(keyword_name), field_id=VALUES(field_id), frequency=VALUES(frequency),
                weight=VALUES(weight), description=VALUES(description), color=VALUES(color), node_size=VALUES(node_size)
                """
                cursor.execute(sql, (
                    keyword.id, keyword.keyword_name, keyword.field_id, keyword.frequency,
                    keyword.weight, keyword.description, keyword.color, keyword.node_size
                ))
            self.connection.commit()
            logger.info(f"插入/更新关键词: {keyword.keyword_name}")
            return True
        except Exception as e:
            logger.error(f"插入关键词失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_paper(self, paper: Paper) -> bool:
        """插入文献信息"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO paper (id, title, abstract, publication_year, venue_id, doi, url, pdf_url,
                                 citations_count, download_count, language, page_start, page_end, 
                                 volume, issue, node_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                title=VALUES(title), abstract=VALUES(abstract), publication_year=VALUES(publication_year),
                venue_id=VALUES(venue_id), doi=VALUES(doi), url=VALUES(url), pdf_url=VALUES(pdf_url),
                citations_count=VALUES(citations_count), download_count=VALUES(download_count),
                language=VALUES(language), page_start=VALUES(page_start), page_end=VALUES(page_end),
                volume=VALUES(volume), issue=VALUES(issue), node_size=VALUES(node_size)
                """
                cursor.execute(sql, (
                    paper.id, paper.title, paper.abstract, paper.publication_year,
                    paper.venue_id, paper.doi, paper.url, paper.pdf_url,
                    paper.citations_count, paper.download_count, paper.language,
                    paper.page_start, paper.page_end, paper.volume, paper.issue, paper.node_size
                ))
            self.connection.commit()
            logger.info(f"插入/更新文献: {paper.title}")
            return True
        except Exception as e:
            logger.error(f"插入文献失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_author(self, author: Author) -> bool:
        """插入作者信息"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO author (id, author_name, author_name_en, affiliation, email, orcid,
                                  homepage, h_index, total_citations, research_interests)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                author_name=VALUES(author_name), author_name_en=VALUES(author_name_en),
                affiliation=VALUES(affiliation), email=VALUES(email), orcid=VALUES(orcid),
                homepage=VALUES(homepage), h_index=VALUES(h_index), total_citations=VALUES(total_citations),
                research_interests=VALUES(research_interests)
                """
                cursor.execute(sql, (
                    author.id, author.author_name, author.author_name_en, author.affiliation,
                    author.email, author.orcid, author.homepage, author.h_index,
                    author.total_citations, author.research_interests
                ))
            self.connection.commit()
            logger.info(f"插入/更新作者: {author.author_name}")
            return True
        except Exception as e:
            logger.error(f"插入作者失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_paper_metadata(self, metadata: PaperMetadata) -> bool:
        """插入文献元数据"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO paper_metadata (paper_id, meta_key, meta_value, meta_type)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                meta_value=VALUES(meta_value), meta_type=VALUES(meta_type)
                """
                cursor.execute(sql, (
                    metadata.paper_id, metadata.meta_key, metadata.meta_value, metadata.meta_type
                ))
            self.connection.commit()
            logger.info(f"插入/更新文献元数据: {metadata.paper_id} - {metadata.meta_key}")
            return True
        except Exception as e:
            logger.error(f"插入文献元数据失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_paper_keyword(self, paper_keyword: PaperKeyword) -> bool:
        """插入文献-关键词映射"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO paper_keyword (paper_id, keyword_id, is_primary, relevance_score)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                is_primary=VALUES(is_primary), relevance_score=VALUES(relevance_score)
                """
                cursor.execute(sql, (
                    paper_keyword.paper_id, paper_keyword.keyword_id,
                    paper_keyword.is_primary, paper_keyword.relevance_score
                ))
            self.connection.commit()
            logger.info(f"插入/更新文献-关键词映射: {paper_keyword.paper_id} - {paper_keyword.keyword_id}")
            return True
        except Exception as e:
            logger.error(f"插入文献-关键词映射失败: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_paper_author(self, paper_author: PaperAuthor) -> bool:
        """插入文献-作者关联"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO paper_author (paper_id, author_id, author_order, is_corresponding, contribution)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                author_order=VALUES(author_order), is_corresponding=VALUES(is_corresponding),
                contribution=VALUES(contribution)
                """
                cursor.execute(sql, (
                    paper_author.paper_id, paper_author.author_id, paper_author.author_order,
                    paper_author.is_corresponding, paper_author.contribution
                ))
            self.connection.commit()
            logger.info(f"插入/更新文献-作者关联: {paper_author.paper_id} - {paper_author.author_id}")
            return True
        except Exception as e:
            logger.error(f"插入文献-作者关联失败: {str(e)}")
            self.connection.rollback()
            return False

def main():
    """主函数"""
    # 测试数据库连接
    db = DatabaseConnector()
    if db.connect():
        logger.info("数据库连接测试成功")
        db.disconnect()
    else:
        logger.error("数据库连接测试失败")

if __name__ == "__main__":
    main()