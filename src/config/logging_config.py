"""
日志配置模块
"""
import logging
from pathlib import Path
from typing import Optional


def setup_logging(log_file: Optional[Path] = None, level: str = "INFO") -> logging.Logger:
    """
    统一的日志配置

    Args:
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        配置好的logger实例
    """
    # 创建logger
    logger = logging.getLogger("kb_create")
    logger.setLevel(getattr(logging, level))

    # 避免重复添加handler
    if not logger.handlers:
        # 创建formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 添加控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 如果指定了日志文件，添加文件handler
        if log_file:
            # 确保日志目录存在
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger