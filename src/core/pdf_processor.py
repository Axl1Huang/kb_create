import subprocess
import logging
import shutil
from pathlib import Path
from typing import List, Optional
import time
from .config import Config

logger = logging.getLogger(__name__)

class PDFProcessor:
    """统一的PDF处理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.mineru_path = config.mineru_path
        
    def find_pdf_files(self, directory: Path) -> List[Path]:
        """查找目录中的所有PDF文件"""
        return list(directory.rglob("*.pdf"))
    
    def process_single_pdf(self, pdf_path: Path, output_dir: Path) -> bool:
        """处理单个PDF文件"""
        try:
            # 创建临时目录
            temp_dir = self.config.paths.temp_dir / f"mineru_{pdf_path.stem}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建命令，确保在正确的conda环境中运行
            cmd = [
                "conda", "run", "-n", "mineru",
                self.mineru_path,
                "-p", str(pdf_path),
                "-o", str(temp_dir),
                # 采用官方CLI参数：backend/device/method/lang
                "-b", "pipeline",
                "-d", "cpu",
                "-m", "auto",
                "-l", "en",
                "--source", "modelscope"
            ]
            
            logger.info(f"处理PDF: {pdf_path.name}")
            logger.info(f"命令: {' '.join(cmd)}")
            logger.info(f"临时目录: {temp_dir}")
            
            # 执行MinerU
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            logger.info(f"MinerU返回码: {result.returncode}")
            if result.stdout:
                logger.info(f"MinerU标准输出: {result.stdout}")
            if result.stderr:
                logger.info(f"MinerU标准错误: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"MinerU处理失败 {pdf_path.name}: {result.stderr}")
                return False
            
            # 查找生成的markdown文件（MinerU会在子目录中生成文件）
            md_files = list(temp_dir.rglob("*.md"))
            if not md_files:
                # 如果在根目录没找到，尝试在auto子目录中查找
                auto_dir = temp_dir / pdf_path.stem / "auto"
                if auto_dir.exists():
                    md_files = list(auto_dir.glob("*.md"))
            
            if not md_files:
                logger.warning(f"未找到Markdown文件: {pdf_path.name}")
                return False
            
            # 移动markdown文件到输出目录
            for md_file in md_files:
                target_file = output_dir / f"{pdf_path.stem}.md"
                shutil.move(str(md_file), str(target_file))
                logger.info(f"生成Markdown: {target_file.name}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"处理超时: {pdf_path.name}")
            return False
        except Exception as e:
            logger.error(f"处理PDF失败 {pdf_path.name}: {e}")
            return False
    
    def process_batch(self, input_dir: Path, output_dir: Path) -> dict:
        """批量处理PDF文件"""
        pdf_files = self.find_pdf_files(input_dir)
        
        if not pdf_files:
            logger.warning("未找到PDF文件")
            return {"processed": 0, "failed": 0, "errors": []}
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {"processed": 0, "failed": 0, "errors": []}
        
        for pdf_file in pdf_files:
            try:
                if self.process_single_pdf(pdf_file, output_dir):
                    results["processed"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(str(pdf_file))
                    
            except Exception as e:
                logger.error(f"处理文件失败 {pdf_file}: {e}")
                results["failed"] += 1
                results["errors"].append(str(pdf_file))
        
        logger.info(f"批处理完成: 成功 {results['processed']}, 失败 {results['failed']}")
        return results