"""
统一的数据导入器 - 优化版本
"""
from .database import DatabaseManager
from ..utils.field_mapping import infer_research_field
import logging
from pathlib import Path
import json
from typing import Dict, Any, Optional, List
from ..utils.progress import progress_wrap
from ..exceptions.processing_error import ProcessingError

logger = logging.getLogger(__name__)


class DataImporter:
    """统一的数据导入器，支持批量操作和缓存"""

    def __init__(self, config):
        self.config = config
        self.db = DatabaseManager(config)
        # 延迟加载解析器，避免在仅进行JSON导入时引入可选模块依赖
        self.parser = None
        # 缓存已创建的实体ID以提高性能
        self._id_cache = {}

    def import_markdown_file(self, md_file: Path) -> bool:
        """导入单个Markdown文件"""
        try:
            md_path = Path(md_file)
            logger.info(f"处理Markdown文件: {md_path.name}")

            # 延迟导入 LLMParser，仅在需要解析Markdown时使用
            if self.parser is None:
                try:
                    from .llm_parser import LLMParser
                    self.parser = LLMParser(self.config)
                except Exception as e:
                    logger.error(f"LLMParser 不可用，无法解析Markdown: {e}")
                    return False

            # 解析Markdown内容
            paper_data = self.parser.parse_markdown_file(str(md_path))
            if not paper_data:
                logger.error(f"解析失败: {md_path.name}")
                return False

            # 导入数据
            return self.import_paper_data(paper_data)

        except Exception as e:
            logger.error(f"导入文件失败 {md_path.name}: {e}")
            return False

    def _get_cached_id(self, table: str, field: str, value: str) -> Optional[str]:
        """从缓存获取ID"""
        key = (table, field, value)
        return self._id_cache.get(key)

    def _set_cached_id(self, table: str, field: str, value: str, record_id: str) -> None:
        """设置缓存ID"""
        key = (table, field, value)
        self._id_cache[key] = record_id

    def import_paper_data(self, data: Dict[str, Any]) -> bool:
        """导入论文数据"""
        try:
            # 获取或创建期刊ID（表: venue, 字段: venue_name）
            venue_id = None
            if data.get('venue'):
                # 先检查缓存
                venue_id = self._get_cached_id('venue', 'venue_name', data['venue'])
                if not venue_id:
                    venue_id = self.db.get_or_create_id(
                        'venue', 'venue_name', data['venue'],
                        additional_fields={
                            'venue_type': 'journal'  # 默认类型，若模型能识别可调整
                        }
                    )
                    # 缓存结果
                    self._set_cached_id('venue', 'venue_name', data['venue'], venue_id)

            # 获取或创建研究领域ID（表: research_field, 字段: field_name）
            # 缺失时尝试根据 venue/keywords/title/abstract 补全映射；若仍无法确定，兜底为 "Environmental Engineering"
            field_id = None
            field_name = data.get('research_field') or infer_research_field(data) or 'Environmental Engineering'
            if field_name:
                # 先检查缓存
                field_id = self._get_cached_id('research_field', 'field_name', field_name)
                if not field_id:
                    field_id = self.db.get_or_create_id(
                        'research_field', 'field_name', field_name
                    )
                    # 缓存结果
                    self._set_cached_id('research_field', 'field_name', field_name, field_id)

            # 插入/更新论文基本信息（表: paper）
            # 优先使用 DOI 查重；无 DOI 时回退按 title 查重
            paper_id = None
            doi_val = data.get('doi')
            if doi_val:
                existing = self.db.execute_query(
                    "SELECT id FROM paper WHERE doi = %s", (doi_val,)
                )
                if existing:
                    paper_id = existing[0]['id']
                    # 使用最新字段更新已存在记录，避免唯一约束冲突
                    self.db.execute_update(
                        """
                        UPDATE paper
                        SET title = %s,
                            abstract = %s,
                            publication_year = %s,
                            venue_id = %s,
                            pdf_url = %s
                        WHERE id = %s
                        """,
                        (
                            data['title'],
                            data.get('abstract', ''),
                            data.get('year'),
                            venue_id,
                            data.get('pdf_path'),
                            paper_id
                        )
                    )

            if not paper_id:
                paper_id = self.db.get_or_create_id(
                    'paper', 'title', data['title'],
                    {
                        'abstract': data.get('abstract', ''),
                        'publication_year': data.get('year'),
                        'venue_id': venue_id,
                        'doi': doi_val,
                        'pdf_url': data.get('pdf_path')
                    }
                )

            # 批量插入作者信息（表: author, 字段: author_name；关联表: paper_author）
            author_inserts = []
            paper_author_inserts = []
            if data.get('authors'):
                for i, author_name in enumerate(data['authors']):
                    # 先检查缓存
                    author_id = self._get_cached_id('author', 'author_name', author_name)
                    if not author_id:
                        author_id = self.db.get_or_create_id(
                            'author', 'author_name', author_name
                        )
                        # 缓存结果
                        self._set_cached_id('author', 'author_name', author_name, author_id)

                    # 准备批量插入数据
                    paper_author_inserts.append((paper_id, author_id, i+1))

                # 批量插入论文-作者关联
                if paper_author_inserts:
                    self.db.execute_batch_update(
                        """INSERT INTO paper_author (paper_id, author_id, author_order)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (paper_id, author_id) DO NOTHING""",
                        paper_author_inserts
                    )

            # 批量插入关键词（表: keyword, 字段: keyword_name；需绑定研究领域 field_id）
            keyword_inserts = []
            paper_keyword_inserts = []
            if data.get('keywords'):
                for keyword in data['keywords']:
                    # 先检查缓存
                    keyword_id = self._get_cached_id('keyword', 'keyword_name', keyword)
                    if not keyword_id:
                        keyword_id = self.db.get_or_create_id(
                            'keyword', 'keyword_name', keyword,
                            additional_fields={'field_id': field_id}
                        )
                        # 缓存结果
                        self._set_cached_id('keyword', 'keyword_name', keyword, keyword_id)

                    # 准备批量插入数据
                    paper_keyword_inserts.append((paper_id, keyword_id))

                # 批量插入论文-关键词关联
                if paper_keyword_inserts:
                    self.db.execute_batch_update(
                        """INSERT INTO paper_keyword (paper_id, keyword_id)
                           VALUES (%s, %s)
                           ON CONFLICT (paper_id, keyword_id) DO NOTHING""",
                        paper_keyword_inserts
                    )

            # 批量插入论文元数据
            metadata_inserts = []
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
                    metadata_inserts.append((paper_id, field, value, meta_type))

            # 批量插入元数据
            if metadata_inserts:
                self.db.execute_batch_update(
                    """INSERT INTO paper_metadata (paper_id, meta_key, meta_value, meta_type)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (paper_id, meta_key) DO NOTHING""",
                    metadata_inserts
                )

            logger.info(f"成功导入论文: {data['title']}")
            return True

        except Exception as e:
            logger.error(f"导入论文数据失败: {e}")
            return False

    def import_batch(self, md_files: list, limit: Optional[int] = None) -> dict:
        """批量导入Markdown文件"""
        results = {"imported": 0, "failed": 0, "errors": []}
        if limit is not None:
            md_files = md_files[: max(0, limit)]

        # 清空缓存以避免内存占用过高
        self._id_cache.clear()

        for md_file in progress_wrap(md_files, desc="数据导入", unit="md"):
            try:
                md_path = Path(md_file)
                if self.import_markdown_file(md_path):
                    results["imported"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(str(md_path))

                # 每处理100个文件清空一次缓存以控制内存使用
                if (results["imported"] + results["failed"]) % 100 == 0:
                    self._id_cache.clear()

            except Exception as e:
                logger.error(f"批量导入失败 {md_path}: {e}")
                results["failed"] += 1
                results["errors"].append(str(md_path))

        logger.info(f"批量导入完成: 成功 {results['imported']}, 失败 {results['failed']}")
        return results

    def clear_cache(self) -> None:
        """清空ID缓存"""
        self._id_cache.clear()
        logger.info("ID缓存已清空")