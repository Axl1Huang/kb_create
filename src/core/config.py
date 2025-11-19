import os
import logging
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Optional

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "knowledge_base"
    sslmode: str = "prefer"

@dataclass
class MinerUConfig:
    """MinerU相关配置"""
    mineru_path: str = ""
    mineru_method: str = "auto"
    mineru_lang: str = "en"
    mineru_model_source: str = "huggingface"
    mineru_timeout_secs: int = 600
    mineru_device: str = ""
    pdf_output_format: str = "md"  # md 或 txt
    pdf_text_only_default: bool = False
    pdf_fast_default: bool = False
    pdf_cleanup_temp: bool = True

@dataclass
class LLMConfig:
    """LLM相关配置"""
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen3-max"
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen3-max"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 300
    num_ctx: int = 8192
    max_chars: int = 100000
    device: Optional[str] = None  # LLM设备配置，如 "cuda:1"

@dataclass
class ParallelConfig:
    """并行处理相关配置"""
    pdf_max_workers: int = 1
    gpu_free_mem_threshold_mb: int = 2048
    gpu_poll_interval_secs: float = 1.0
    gpu_wait_timeout_secs: int = 300

@dataclass
class PathConfig:
    project_root: Path
    input_dir: Path
    output_dir: Path
    processed_dir: Path
    logs_dir: Path
    temp_dir: Path

    @classmethod
    def from_env(cls):
        # 默认使用当前环境的项目根目录 /root/kb_create
        root = Path(os.getenv('PROJECT_ROOT', '/root/kb_create'))
        return cls(
            project_root=root,
            input_dir=Path(os.getenv('INPUT_DIR', root / 'data' / 'input')),
            output_dir=Path(os.getenv('OUTPUT_DIR', root / 'data' / 'output')),
            processed_dir=Path(os.getenv('PROCESSED_DIR', root / 'data' / 'processed')),
            logs_dir=Path(os.getenv('LOGS_DIR', root / 'logs')),
            temp_dir=Path(os.getenv('TEMP_DIR', root / 'temp'))
        )

class UnifiedConfig:
    """统一配置管理类"""
    def __init__(self, config_path: str = None):
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

        self.db = DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'knowledge_base'),
            sslmode=os.getenv('DB_SSLMODE', 'require')
        )

        self.mineru = MinerUConfig(
            mineru_path=os.getenv('MINERU_PATH', ''),
            mineru_method=os.getenv('MINERU_METHOD', 'auto'),
            mineru_lang=os.getenv('MINERU_LANG', 'en'),
            mineru_model_source=os.getenv('MINERU_MODEL_SOURCE', 'huggingface'),
            mineru_timeout_secs=int(os.getenv('MINERU_TIMEOUT_SECS', '600')),
            mineru_device=os.getenv('MINERU_DEVICE', ''),
            pdf_output_format=os.getenv('PDF_OUTPUT_FORMAT', 'md'),
            pdf_text_only_default=os.getenv('PDF_TEXT_ONLY_DEFAULT', 'False').lower() == 'true',
            pdf_fast_default=os.getenv('MINERU_FAST_DEFAULT', 'False').lower() == 'true',
            pdf_cleanup_temp=os.getenv('PDF_CLEANUP_TEMP', 'True').lower() == 'true'
        )

        self.llm = LLMConfig(
            dashscope_api_key=os.getenv('DASHSCOPE_API_KEY', ''),
            dashscope_model=os.getenv('DASHSCOPE_MODEL', 'qwen3-max'),
            ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            model=os.getenv('LLM_MODEL', 'qwen3-max'),
            temperature=float(os.getenv('LLM_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '0')),
            timeout=int(os.getenv('LLM_TIMEOUT', '0')),
            num_ctx=int(os.getenv('LLM_NUM_CTX', '32768')),
            max_chars=int(os.getenv('LLM_MAX_CHARS', '0')),
            device=os.getenv('LLM_DEVICE', None)
        )

        self.parallel = ParallelConfig(
            pdf_max_workers=int(os.getenv('PDF_MAX_WORKERS', '1')),
            gpu_free_mem_threshold_mb=int(os.getenv('GPU_FREE_MEM_THRESHOLD_MB', '2048')),
            gpu_poll_interval_secs=float(os.getenv('GPU_POLL_INTERVAL_SECS', '1.0')),
            gpu_wait_timeout_secs=int(os.getenv('GPU_WAIT_TIMEOUT_SECS', '300'))
        )

        self.paths = PathConfig.from_env()

    def setup_directories(self):
        """创建必要的目录"""
        for path in [
            self.paths.input_dir,
            self.paths.output_dir,
            self.paths.processed_dir,
            self.paths.logs_dir,
            self.paths.temp_dir
        ]:
            path.mkdir(parents=True, exist_ok=True)

class Config:
    """向后兼容的配置类"""
    def __init__(self, config_path: str = None):
        self._unified_config = UnifiedConfig(config_path)
        # 保持原有属性以确保向后兼容
        self.llm = self._unified_config.llm
        self.db = self._unified_config.db
        self.paths = self._unified_config.paths
        self.mineru_path = self._unified_config.mineru.mineru_path
        self.mineru_method = self._unified_config.mineru.mineru_method
        self.mineru_lang = self._unified_config.mineru.mineru_lang
        self.mineru_model_source = self._unified_config.mineru.mineru_model_source
        self.dashscope_api_key = self._unified_config.llm.dashscope_api_key
        self.dashscope_model = self._unified_config.llm.dashscope_model
        self.pdf_output_format = self._unified_config.mineru.pdf_output_format
        self.pdf_text_only_default = self._unified_config.mineru.pdf_text_only_default
        self.pdf_fast_default = self._unified_config.mineru.pdf_fast_default
        self.pdf_cleanup_temp = self._unified_config.mineru.pdf_cleanup_temp
        self.mineru_timeout_secs = self._unified_config.mineru.mineru_timeout_secs
        self.mineru_device = self._unified_config.mineru.mineru_device
        self.pdf_max_workers = self._unified_config.parallel.pdf_max_workers
        self.gpu_free_mem_threshold_mb = self._unified_config.parallel.gpu_free_mem_threshold_mb
        self.gpu_poll_interval_secs = self._unified_config.parallel.gpu_poll_interval_secs
        self.gpu_wait_timeout_secs = self._unified_config.parallel.gpu_wait_timeout_secs

    def setup_directories(self):
        """创建必要的目录"""
        self._unified_config.setup_directories()

def setup_logging(log_file: Path, level: str = "INFO"):
    """统一的日志配置"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)