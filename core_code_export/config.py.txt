import os
import logging
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "knowledge_base"
    sslmode: str = "prefer"

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

class Config:
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
        self.paths = PathConfig.from_env()
        # MinerU CLI路径（可留空，PDFProcessor会自动探测）
        self.mineru_path = os.getenv('MINERU_PATH', '')
        # MinerU 处理选项
        self.mineru_method = os.getenv('MINERU_METHOD', 'auto')
        self.mineru_lang = os.getenv('MINERU_LANG', 'en')
        self.mineru_model_source = os.getenv('MINERU_MODEL_SOURCE', 'huggingface')
        self.dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
        self.dashscope_model = os.getenv('DASHSCOPE_MODEL', 'qwen3-max')
        # PDF 处理行为配置（可通过环境覆盖）
        self.pdf_output_format = os.getenv('PDF_OUTPUT_FORMAT', 'md')  # md 或 txt
        self.pdf_text_only_default = os.getenv('PDF_TEXT_ONLY_DEFAULT', 'False').lower() == 'true'
        self.pdf_fast_default = os.getenv('MINERU_FAST_DEFAULT', 'False').lower() == 'true'
        self.pdf_cleanup_temp = os.getenv('PDF_CLEANUP_TEMP', 'True').lower() == 'true'
        self.mineru_timeout_secs = int(os.getenv('MINERU_TIMEOUT_SECS', '600'))
        # 可强制设备：cuda:0 / cpu；为空时自动探测
        self.mineru_device = os.getenv('MINERU_DEVICE', '')
        
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