from .database import DatabaseManager
from .llm_parser import LLMParser
import logging
from pathlib import Path
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DataImporter:
    """统一的数据导入器"""
    
    def __init__(self, config):
        self.config = config
        self.db = DatabaseManager(config)
        self.parser = LLMParser(config)
    
    def import_markdown_file(self, md_file: Path) -> bool:
        """导入单个Markdown文件"""
        try:
            logger.info(f"处理Markdown文件: {md_file.name}")
            
            # 解析Markdown内容
            paper_data = self.parser.parse_markdown_file(str(md_file))
            if not paper_data:
                logger.error(f"解析失败: {md_file.name}")
                return False
            
            # 导入数据
            return self.import_paper_data(paper_data)
            
        except Exception as e:
            logger.error(f"导入文件失败 {md_file.name}: {e}")
            return False
    
    def import_paper_data(self, data: Dict[str, Any]) -> bool:
        """导入论文数据"""
        try:
            # 获取或创建期刊ID（表: venue, 字段: venue_name）
            venue_id = None
            if data.get('venue'):
                venue_id = self.db.get_or_create_id(
                    'venue', 'venue_name', data['venue'],
                    additional_fields={
                        'venue_type': 'journal'  # 默认类型，若模型能识别可调整
                    }
                )
            
            # 获取或创建研究领域ID（表: research_field, 字段: field_name）
            field_id = None
            if data.get('research_field'):
                field_id = self.db.get_or_create_id(
                    'research_field', 'field_name', data['research_field']
                )
            
            # 插入论文基本信息（表: paper）
            paper_id = self.db.get_or_create_id(
                'paper', 'title', data['title'],
                {
                    'abstract': data.get('abstract', ''),
                    'publication_year': data.get('year'),
                    'venue_id': venue_id,
                    'doi': data.get('doi'),
                    'pdf_url': data.get('pdf_path')
                }
            )
            
            # 插入作者信息（表: author, 字段: author_name；关联表: paper_author）
            if data.get('authors'):
                for i, author_name in enumerate(data['authors']):
                    author_id = self.db.get_or_create_id(
                        'author', 'author_name', author_name
                    )
                    # 建立论文-作者关联
                    self.db.execute_update(
                        """INSERT INTO paper_author (paper_id, author_id, author_order) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (paper_id, author_id) DO NOTHING""",
                        (paper_id, author_id, i+1)
                    )
            
            # 插入关键词（表: keyword, 字段: keyword_name；需绑定研究领域 field_id）
            if data.get('keywords'):
                for keyword in data['keywords']:
                    keyword_id = self.db.get_or_create_id(
                        'keyword', 'keyword_name', keyword,
                        additional_fields={'field_id': field_id} if field_id else None
                    )
                    # 建立论文-关键词关联
                    self.db.execute_update(
                        """INSERT INTO paper_keyword (paper_id, keyword_id) 
                           VALUES (%s, %s) 
                           ON CONFLICT (paper_id, keyword_id) DO NOTHING""",
                        (paper_id, keyword_id)
                    )
            
            # 插入论文元数据
            metadata_fields = [
                'hrt_conditions', 'pollutants', 'cod_removal_efficiency',
                'enzyme_activities', 'references'
            ]
            
            for field in metadata_fields:
                if data.get(field):
                    value = data[field]
                    if isinstance(value, list):
                        value = json.dumps(value)
                    
                    # 适配实际表结构: paper_metadata(meta_key, meta_value, meta_type)
                    meta_type = 'json' if isinstance(data[field], list) else 'text'
                    self.db.execute_update(
                        """INSERT INTO paper_metadata (paper_id, meta_key, meta_value, meta_type)
                           VALUES (%s, %s, %s, %s) 
                           ON CONFLICT (paper_id, meta_key) DO NOTHING""",
                        (paper_id, field, value, meta_type)
                    )
            
            logger.info(f"成功导入论文: {data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"导入论文数据失败: {e}")
            return False
    
    def import_batch(self, md_files: list) -> dict:
        """批量导入Markdown文件"""
        results = {"imported": 0, "failed": 0, "errors": []}
        
        for md_file in md_files:
            try:
                if self.import_markdown_file(md_file):
                    results["imported"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(str(md_file))
                    
            except Exception as e:
                logger.error(f"批量导入失败 {md_file}: {e}")
                results["failed"] += 1
                results["errors"].append(str(md_file))
        
        logger.info(f"批量导入完成: 成功 {results['imported']}, 失败 {results['failed']}")
        return results