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
        root = Path(os.getenv('PROJECT_ROOT', '/home/axlhuang/kb_create'))
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
            load_dotenv(dotenv_path=config_path)
        else:
            # 默认加载项目根目录下的 config/config.env
            project_root = Path(os.getenv('PROJECT_ROOT', '/home/axlhuang/kb_create'))
            env_path = project_root / 'config' / 'config.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
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
        self.mineru_path = os.getenv('MINERU_PATH', '/home/axlhuang/miniconda3/envs/mineru/bin/mineru')
        self.dashscope_api_key = os.getenv('DASHSCOPE_API_KEY')
        self.dashscope_model = os.getenv('DASHSCOPE_MODEL', 'qwen3-max')
        
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