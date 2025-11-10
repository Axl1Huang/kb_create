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
        self.mineru_path = self._detect_mineru_path(config.mineru_path)

    def _detect_mineru_path(self, configured_path: Optional[str]) -> Optional[str]:
        """自动探测可用的 MinerU/Magic-PDF CLI 路径。
        优先级：显式配置 > PATH中的 mineru > PATH中的 magic-pdf
        返回可执行命令名或绝对路径；若不可用返回 None。
        """
        import shutil
        # 显式配置存在且可执行
        if configured_path:
            p = Path(configured_path)
            if p.exists():
                return str(p)
        # PATH 中的 mineru
        m = shutil.which("mineru")
        if m:
            return m
        # PATH 中的 magic-pdf（旧名/子模块）
        mp = shutil.which("magic-pdf")
        if mp:
            return mp
        return None
        
    def find_pdf_files(self, directory: Path) -> List[Path]:
        """查找目录中的所有PDF文件"""
        return list(directory.rglob("*.pdf"))
    
    def _md_to_txt(self, content: str) -> str:
        """将Markdown内容转换为纯文本，去除图片/链接/格式标记。"""
        import re
        # 删除代码块
        content = re.sub(r"```[\s\S]*?```", "\n", content)
        # 删除图片
        content = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", content)
        # 将链接替换为其文本
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
        # 去掉标题标记 #
        content = re.sub(r"^\s*#{1,6}\s*", "", content, flags=re.MULTILINE)
        # 去掉强调 * 和 _
        content = re.sub(r"[*_]+", "", content)
        # 简化列表项前缀
        content = re.sub(r"^[\s>*-]+", "", content, flags=re.MULTILINE)
        # 去掉表格分隔线
        content = re.sub(r"^\s*\|?\s*-{2,}.*$", "", content, flags=re.MULTILINE)
        # 压缩多余空行
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def process_single_pdf(self, pdf_path: Path, output_dir: Path, output_format: str = "md", text_only: bool = False, device: Optional[str] = None, language: Optional[str] = None, fast: bool = False, start_page: Optional[int] = None, end_page: Optional[int] = None) -> bool:
        """处理单个PDF文件
        - output_format: "md" 或 "txt"
        - text_only: True 时清理非文本类产物（图片等）
        - device: 指定设备，如 "cuda:0" 或 "cpu"；默认使用GPU可用则CUDA，否则CPU
        - fast: True 时关闭公式/表格解析以加速，可能降低对复杂版式的还原
        """
        try:
            # 创建临时目录
            temp_dir = self.config.paths.temp_dir / f"mineru_{pdf_path.stem}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建命令：优先直接调用 CLI，无需 conda。回退到 magic-pdf 语法。
            if not self.mineru_path:
                raise RuntimeError("未检测到 MinerU/magic-pdf CLI，请先安装 MinerU: `pip install -U \"mineru[core]\"` 或 `pip install magic-pdf`. ")
            # 设备优先选择GPU；若配置指定则优先使用配置
            if device is None:
                if self.config.mineru_device:
                    device = self.config.mineru_device
                else:
                    try:
                        import torch
                        device = "cuda:0" if torch.cuda.is_available() else "cpu"
                    except Exception:
                        device = "cpu"
            # 读取配置默认值（方法/语言/模型源）
            method = (self.config.mineru_method or "auto").strip()
            lang = (language or self.config.mineru_lang or "en").strip()
            model_source = (self.config.mineru_model_source or "huggingface").strip()

            if Path(self.mineru_path).name == "magic-pdf":
                # magic-pdf 语法：magic-pdf -p <pdf> -o <dir> -m auto -l en
                cmd = [
                    self.mineru_path,
                    "-p", str(pdf_path),
                    "-o", str(temp_dir),
                    "-m", method,
                    "--lang", lang
                ]
            else:
                # mineru CLI 语法：mineru -p <input> -o <output> -b pipeline -d cpu -m auto -l en --source modelscope
                cmd = [
                    self.mineru_path,
                    "-p", str(pdf_path),
                    "-o", str(temp_dir),
                    "-b", "pipeline",
                    "-d", device,
                    "-m", method,
                    "-l", lang,
                    "--source", model_source
                ]
            # 页码范围（0 基，仅在 mineru CLI 下可用）
            if Path(self.mineru_path).name != "magic-pdf":
                if start_page is not None:
                    cmd += ["-s", str(start_page)]
                if end_page is not None:
                    cmd += ["-e", str(end_page)]
            # 快速模式：尽量减少非文本内容的解析（关闭公式/表格）
            if fast:
                cmd += ["-f", "False", "-t", "False"]
            
            logger.info(f"处理PDF: {pdf_path.name}")
            logger.info(f"命令: {' '.join(cmd)}")
            logger.info(f"临时目录: {temp_dir}")
            
            # 执行MinerU
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.mineru_timeout_secs
            )
            
            logger.info(f"MinerU返回码: {result.returncode}")
            if result.stdout:
                logger.info(f"MinerU标准输出: {result.stdout}")
            if result.stderr:
                logger.info(f"MinerU标准错误: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"MinerU处理失败 {pdf_path.name}: {result.stderr}")
                return False
            
            # 查找生成的文本/markdown文件（MinerU会在子目录中生成文件）
            md_files = list(temp_dir.rglob("*.md"))
            txt_files = list(temp_dir.rglob("*.txt"))
            if not md_files and not txt_files:
                # 如果在根目录没找到，尝试在auto子目录中查找
                auto_dir = temp_dir / pdf_path.stem / "auto"
                if auto_dir.exists():
                    md_files = list(auto_dir.glob("*.md"))
                    txt_files = list(auto_dir.glob("*.txt"))
            
            if output_format == "txt":
                # 优先直接使用MinerU产生的txt，否则从md转换
                if txt_files:
                    src = txt_files[0]
                    target_file = output_dir / f"{pdf_path.stem}.txt"
                    shutil.move(str(src), str(target_file))
                    logger.info(f"生成TXT: {target_file.name}")
                elif md_files:
                    src = md_files[0]
                    text = Path(src).read_text(encoding="utf-8", errors="ignore")
                    text = self._md_to_txt(text)
                    target_file = output_dir / f"{pdf_path.stem}.txt"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    Path(target_file).write_text(text, encoding="utf-8")
                    logger.info(f"从MD转换生成TXT: {target_file.name}")
                else:
                    logger.warning(f"未找到可生成TXT的文件: {pdf_path.name}")
                    return False
            else:
                if not md_files:
                    logger.warning(f"未找到Markdown文件: {pdf_path.name}")
                    return False
                src = md_files[0]
                target_file = output_dir / f"{pdf_path.stem}.md"
                shutil.move(str(src), str(target_file))
                logger.info(f"生成Markdown: {target_file}")

            # 清理非文本类产物
            if text_only:
                try:
                    for p in temp_dir.rglob("*"):
                        if p.is_file() and p.suffix.lower() not in {".txt", ".md"}:
                            p.unlink(missing_ok=True)
                    # 删除空目录
                    for d in sorted([d for d in temp_dir.rglob("*") if d.is_dir()], reverse=True):
                        if not any(d.iterdir()):
                            d.rmdir()
                except Exception as ce:
                    logger.warning(f"清理非文本产物时出错: {ce}")
            
            # 清理临时目录（受配置开关控制）
            if self.config.pdf_cleanup_temp:
                shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                logger.info(f"保留临时目录以便调试: {temp_dir}")
            
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
        
        # 从配置读取默认处理选项
        default_output_format = self.config.pdf_output_format
        default_text_only = self.config.pdf_text_only_default
        default_fast = self.config.pdf_fast_default
        default_device = self.config.mineru_device or None
        default_language = self.config.mineru_lang

        for pdf_file in pdf_files:
            try:
                if self.process_single_pdf(
                    pdf_file,
                    output_dir,
                    output_format=default_output_format,
                    text_only=default_text_only,
                    device=default_device,
                    language=default_language,
                    fast=default_fast
                ):
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