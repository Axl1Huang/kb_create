"""
配置管理器 - 负责加载和管理所有配置参数
"""
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "knowledge_base"
    sslmode: str = "prefer"

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """从环境变量创建数据库配置"""
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'knowledge_base'),
            sslmode=os.getenv('DB_SSLMODE', 'prefer')
        )


@dataclass
class PathConfig:
    """路径配置"""
    project_root: Path
    input_dir: Path
    output_dir: Path
    processed_dir: Path
    logs_dir: Path
    temp_dir: Path

    @classmethod
    def from_env(cls) -> 'PathConfig':
        """从环境变量创建路径配置"""
        # 默认使用当前环境的项目根目录
        root = Path(os.getenv('PROJECT_ROOT', '/root/kb_create'))
        return cls(
            project_root=root,
            input_dir=Path(os.getenv('INPUT_DIR', root / 'data' / 'input')),
            output_dir=Path(os.getenv('OUTPUT_DIR', root / 'data' / 'output')),
            processed_dir=Path(os.getenv('PROCESSED_DIR', root / 'data' / 'processed')),
            logs_dir=Path(os.getenv('LOGS_DIR', root / 'logs')),
            temp_dir=Path(os.getenv('TEMP_DIR', root / 'temp'))
        )


@dataclass
class LLMConfig:
    """LLM配置"""
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen3:30b"
    temperature: float = 0.1
    max_tokens: int = 8192
    timeout: int = 600
    num_ctx: int = 16384
    max_chars: int = 0
    dashscope_api_key: Optional[str] = None
    dashscope_model: str = "qwen3-max"

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """从环境变量创建LLM配置"""
        return cls(
            ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            model=os.getenv('MODEL', 'qwen3:30b'),
            temperature=float(os.getenv('TEMPERATURE', '0.1')),
            max_tokens=int(os.getenv('MAX_TOKENS', '8192')),
            timeout=int(os.getenv('TIMEOUT', '600')),
            num_ctx=int(os.getenv('NUM_CTX', '16384')),
            max_chars=int(os.getenv('MAX_CHARS', '0')),
            dashscope_api_key=os.getenv('DASHSCOPE_API_KEY'),
            dashscope_model=os.getenv('DASHSCOPE_MODEL', 'qwen3-max')
        )


@dataclass
class PDFConfig:
    """PDF处理配置"""
    mineru_path: str = ""
    mineru_method: str = "auto"
    mineru_lang: str = "en"
    mineru_model_source: str = "huggingface"
    mineru_device: str = ""
    mineru_timeout_secs: int = 600
    pdf_output_format: str = "md"
    pdf_text_only_default: bool = False
    pdf_fast_default: bool = False
    pdf_cleanup_temp: bool = True
    pdf_max_workers: int = 1
    gpu_free_mem_threshold_mb: int = 2048
    gpu_poll_interval_secs: float = 1.0
    gpu_wait_timeout_secs: int = 300

    @classmethod
    def from_env(cls) -> 'PDFConfig':
        """从环境变量创建PDF配置"""
        return cls(
            mineru_path=os.getenv('MINERU_PATH', ''),
            mineru_method=os.getenv('MINERU_METHOD', 'auto'),
            mineru_lang=os.getenv('MINERU_LANG', 'en'),
            mineru_model_source=os.getenv('MINERU_MODEL_SOURCE', 'huggingface'),
            mineru_device=os.getenv('MINERU_DEVICE', ''),
            mineru_timeout_secs=int(os.getenv('MINERU_TIMEOUT_SECS', '600')),
            pdf_output_format=os.getenv('PDF_OUTPUT_FORMAT', 'md'),
            pdf_text_only_default=os.getenv('PDF_TEXT_ONLY_DEFAULT', 'False').lower() == 'true',
            pdf_fast_default=os.getenv('MINERU_FAST_DEFAULT', 'False').lower() == 'true',
            pdf_cleanup_temp=os.getenv('PDF_CLEANUP_TEMP', 'True').lower() == 'true',
            pdf_max_workers=int(os.getenv('PDF_MAX_WORKERS', '1')),
            gpu_free_mem_threshold_mb=int(os.getenv('GPU_FREE_MEM_THRESHOLD_MB', '2048')),
            gpu_poll_interval_secs=float(os.getenv('GPU_POLL_INTERVAL_SECS', '1.0')),
            gpu_wait_timeout_secs=int(os.getenv('GPU_WAIT_TIMEOUT_SECS', '300'))
        )


class Config:
    """主配置类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        # 加载配置文件
        self._load_config(config_path)

        # 创建各子配置
        self.db = DatabaseConfig.from_env()
        self.paths = PathConfig.from_env()
        self.llm = LLMConfig.from_env()
        self.pdf = PDFConfig.from_env()

    def _load_config(self, config_path: Optional[str] = None) -> None:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径
        """
        if config_path:
            # 允许项目内配置覆盖环境变量，确保路径一致
            load_dotenv(dotenv_path=config_path, override=True)
        else:
            # 默认加载项目根目录下的 config/config.env
            project_root = Path(os.getenv('PROJECT_ROOT', '/root/kb_create'))
            env_path = project_root / 'config' / 'config.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
            else:
                print(f"警告: 默认配置文件 {env_path} 不存在，将依赖环境变量。")

    def setup_directories(self) -> None:
        """创建必要的目录"""
        directories = [
            self.paths.input_dir,
            self.paths.output_dir,
            self.paths.processed_dir,
            self.paths.logs_dir,
            self.paths.temp_dir
        ]

        for path in directories:
            path.mkdir(parents=True, exist_ok=True)
            logging.info(f"确保目录存在: {path}")