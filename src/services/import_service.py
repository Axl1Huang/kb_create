"""
数据导入服务
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..config import Config
from ..core.data_importer import DataImporter

logger = logging.getLogger(__name__)


class ImportService:
    """数据导入服务"""

    def __init__(self, config: Config):
        """
        初始化数据导入服务

        Args:
            config: 配置对象
        """
        self.config = config
        self.importer = DataImporter(config)

    def import_paper_data(self, data: Dict[str, Any]) -> bool:
        """
        导入论文数据

        Args:
            data: 论文数据字典

        Returns:
            导入是否成功
        """
        try:
            result = self.importer.import_paper_data(data)
            if result:
                logger.info(f"成功导入论文: {data.get('title', 'Unknown')}")
            else:
                logger.error(f"导入论文失败: {data.get('title', 'Unknown')}")
            return result
        except Exception as e:
            logger.error(f"导入论文数据时发生异常: {e}")
            return False

    def import_batch(self, md_files: List[Path], limit: Optional[int] = None) -> dict:
        """
        批量导入Markdown文件

        Args:
            md_files: Markdown文件路径列表
            limit: 限制处理文件数量

        Returns:
            导入结果字典
        """
        logger.info("开始批量数据导入")
        results = self.importer.import_batch(md_files, limit=limit)
        logger.info(f"数据导入完成: 成功 {results['imported']}, 失败 {results['failed']}")
        return results