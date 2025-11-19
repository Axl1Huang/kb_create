"""
解析服务
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from ..config import Config
from ..core.llm_parser import LLMParser

logger = logging.getLogger(__name__)


class ParsingService:
    """解析服务"""

    def __init__(self, config: Config):
        """
        初始化解析服务

        Args:
            config: 配置对象
        """
        self.config = config
        self.parser = LLMParser(config)

    def parse_markdown_file(self, md_file: Path) -> Dict[str, Any]:
        """
        解析Markdown文件

        Args:
            md_file: Markdown文件路径

        Returns:
            解析后的数据字典
        """
        logger.info(f"解析Markdown文件: {md_file.name}")
        try:
            data = self.parser.parse_markdown_file(str(md_file))
            logger.info(f"成功解析文件: {md_file.name}")
            return data
        except Exception as e:
            logger.error(f"解析文件失败 {md_file.name}: {e}")
            raise

    def parse_batch(self, md_files: List[Path], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        批量解析Markdown文件

        Args:
            md_files: Markdown文件路径列表
            limit: 限制处理文件数量

        Returns:
            解析后的数据字典列表
        """
        if limit is not None:
            md_files = md_files[:limit]

        results = []
        for md_file in md_files:
            try:
                data = self.parse_markdown_file(md_file)
                results.append(data)
            except Exception as e:
                logger.error(f"批量解析失败 {md_file}: {e}")
                # 继续处理其他文件而不是中断整个批处理

        return results