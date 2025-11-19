"""
PDF处理服务
"""
import logging
from typing import List, Optional
from pathlib import Path
from ..config import Config
from ..core.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class PDFService:
    """PDF处理服务"""

    def __init__(self, config: Config):
        """
        初始化PDF服务

        Args:
            config: 配置对象
        """
        self.config = config
        self.processor = PDFProcessor(config)

    def process_batch(self, input_dir: Optional[Path] = None,
                     output_dir: Optional[Path] = None,
                     limit: Optional[int] = None,
                     stats_every: Optional[int] = None) -> dict:
        """
        批量处理PDF文件

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            limit: 限制处理文件数量
            stats_every: 每处理N个文件输出统计信息

        Returns:
            处理结果字典
        """
        input_path = input_dir or self.config.paths.input_dir
        output_path = output_dir or self.config.paths.output_dir / "markdown"

        logger.info("开始批量PDF处理")
        results = self.processor.process_batch(
            input_path,
            output_path,
            limit=limit,
            stats_every=stats_every
        )
        logger.info(f"PDF批处理完成: 成功 {results['processed']}, 失败 {results['failed']}")
        return results

    def process_single(self, pdf_path: Path, output_dir: Optional[Path] = None) -> bool:
        """
        处理单个PDF文件

        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录

        Returns:
            处理是否成功
        """
        output_path = output_dir or self.config.paths.output_dir / "markdown"
        return self.processor.process_single_pdf(
            pdf_path,
            output_path,
            output_format=self.config.pdf.pdf_output_format,
            text_only=self.config.pdf.pdf_text_only_default,
            device=self.config.pdf.mineru_device or None,
            language=self.config.pdf.mineru_lang,
            fast=self.config.pdf.pdf_fast_default
        )