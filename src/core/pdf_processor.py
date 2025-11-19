import subprocess
import logging
import shutil
from pathlib import Path
from typing import List, Optional
import time
import json
from datetime import datetime
from ..config import Config
from ..utils.progress import progress_wrap
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import torch  # 用于GPU可用性与内存查询
except Exception:
    torch = None

logger = logging.getLogger(__name__)

class PDFProcessor:
    """统一的PDF处理器"""

    def __init__(self, config: Config):
        self.config = config
        # 兼容旧的Config类和新的UnifiedConfig类
        if hasattr(config, 'mineru'):
            # 新的UnifiedConfig
            self.mineru_path = self._detect_mineru_path(config.mineru.mineru_path)
        else:
            # 旧的Config类
            self.mineru_path = self._detect_mineru_path(config.mineru_path)
        # MinerU日志文件目录
        try:
            self.mineru_logs_dir = self.config.paths.logs_dir / "mineru"
            self.mineru_logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"创建MinerU日志目录失败: {e}")

    def _get_config_attr(self, attr_name, default=None):
        """获取配置属性的兼容方法"""
        # 检查是否是新的UnifiedConfig
        if hasattr(self.config, 'mineru'):
            # 处理mineru相关的属性
            if attr_name.startswith('mineru_'):
                return getattr(self.config.mineru, attr_name, default)
            # 处理parallel相关的属性
            elif attr_name.startswith('gpu_') or attr_name == 'pdf_max_workers':
                return getattr(self.config.parallel, attr_name, default)
            # 处理pdf相关的属性
            elif attr_name.startswith('pdf_'):
                return getattr(self.config.mineru, attr_name, default)
            # 其他属性
            else:
                return getattr(self.config, attr_name, default)
        else:
            # 旧的Config类
            return getattr(self.config, attr_name, default)

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

    def _is_already_processed(self, pdf_file: Path, output_dir: Path) -> bool:
        """判断PDF是否已处理过。
        判定依据：
        1) 目标输出文件是否已存在（md 或 txt，取决于配置）
        2) 已处理标记文件是否存在（processed_dir/<stem>.done）
        """
        try:
            suffix = (self._get_config_attr('pdf_output_format') or "md").lower()
            expected = output_dir / f"{pdf_file.stem}.{suffix}"
            if expected.exists():
                return True
            marker = self.config.paths.processed_dir / f"{pdf_file.stem}.done"
            if marker.exists():
                return True
        except Exception:
            # 任意异常均视为未处理，避免误判导致跳过
            return False
        return False

    def _write_processed_marker(self, pdf_file: Path) -> None:
        """写入已处理标记文件，包含时间戳与原始路径。"""
        try:
            self.config.paths.processed_dir.mkdir(parents=True, exist_ok=True)
            marker = self.config.paths.processed_dir / f"{pdf_file.stem}.done"
            record = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "pdf_path": str(pdf_file)
            }
            marker.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"写入已处理标记失败: {e}")
    
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
                if self._get_config_attr('mineru_device'):
                    device = self._get_config_attr('mineru_device')
                else:
                    try:
                        import torch
                        device = "cuda:0" if torch.cuda.is_available() else "cpu"
                    except Exception:
                        device = "cpu"
            # 读取配置默认值（方法/语言/模型源）
            method = (self._get_config_attr('mineru_method') or "auto").strip()
            lang = (language or self._get_config_attr('mineru_lang') or "en").strip()
            model_source = (self._get_config_attr('mineru_model_source') or "huggingface").strip()

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
            # 将MinerU输出重定向到日志文件，降低内存占用
            out_log = self.mineru_logs_dir / f"{pdf_path.stem}.out.log"
            err_log = self.mineru_logs_dir / f"{pdf_path.stem}.err.log"
            with open(out_log, "w", encoding="utf-8", errors="ignore") as out_fh, \
                 open(err_log, "w", encoding="utf-8", errors="ignore") as err_fh:
                result = subprocess.run(
                    cmd,
                    stdout=out_fh,
                    stderr=err_fh,
                    text=True,
                    timeout=self._get_config_attr('mineru_timeout_secs')
                )
            
            logger.info(f"MinerU返回码: {result.returncode} | 日志: out={out_log} err={err_log}")
            
            if result.returncode != 0:
                logger.error(f"MinerU处理失败 {pdf_path.name}，详见日志: {err_log}")
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
                # 期望生成Markdown；若直接没有MD则尝试使用TXT兜底包装为Markdown
                if not md_files:
                    if txt_files:
                        # 兜底：将TXT包装为Markdown（标题+正文）
                        src_txt = txt_files[0]
                        text = Path(src_txt).read_text(encoding="utf-8", errors="ignore")
                        md_content = f"# {pdf_path.stem}\n\n" + text.strip() + "\n"
                        output_dir.mkdir(parents=True, exist_ok=True)
                        target_file = output_dir / f"{pdf_path.stem}.md"
                        Path(target_file).write_text(md_content, encoding="utf-8")
                        logger.info(f"兜底转换: 从TXT包装生成Markdown: {target_file.name}")
                    else:
                        logger.warning(f"未找到Markdown文件: {pdf_path.name}")
                        return False
                else:
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
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"处理超时: {pdf_path.name}")
            return False
        except Exception as e:
            logger.error(f"处理PDF失败 {pdf_path.name}: {e}")
            return False
        finally:
            # 始终根据配置尝试清理临时目录（包括失败场景），避免残留空目录
            try:
                if 'temp_dir' in locals():
                    if self._get_config_attr('pdf_cleanup_temp'):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    else:
                        # 保留用于调试的完整结构
                        logger.info(f"保留临时目录以便调试: {temp_dir}")
            except Exception as ce:
                logger.warning(f"清理临时目录失败: {ce}")
    
    def _get_free_gpu_mem_mb(self, device_index: int = 0) -> Optional[float]:
        """查询指定GPU的空闲显存(MB)。优先使用torch，其次nvidia-smi。失败返回None。"""
        # torch 优先
        try:
            if torch is not None and torch.cuda.is_available():
                free_bytes, total_bytes = torch.cuda.mem_get_info(device_index)
                return float(free_bytes) / (1024.0 ** 2)
        except Exception:
            pass
        # nvidia-smi 回退
        try:
            smi = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True
            )
            if smi.returncode == 0 and smi.stdout:
                lines = [l.strip() for l in smi.stdout.splitlines() if l.strip()]
                if not lines:
                    return None
                # 仅使用第一个GPU的结果
                return float(lines[device_index])
        except Exception:
            pass
        return None

    def _wait_for_gpu(self) -> bool:
        """根据配置等待GPU空闲显存达到阈值。超时返回False。"""
        threshold = max(0, self._get_config_attr('gpu_free_mem_threshold_mb'))
        poll = max(0.1, self._get_config_attr('gpu_poll_interval_secs'))
        timeout = max(0, self._get_config_attr('gpu_wait_timeout_secs'))
        if threshold == 0:
            return True
        start = time.time()
        while True:
            free_mb = self._get_free_gpu_mem_mb(device_index=0)
            if free_mb is not None and free_mb >= threshold:
                return True
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(poll)

    def process_batch(self, input_dir: Path, output_dir: Path, limit: Optional[int] = None, stats_every: Optional[int] = None) -> dict:
        """批量处理PDF文件"""
        pdf_files = self.find_pdf_files(input_dir)
        if limit is not None:
            pdf_files = pdf_files[: max(0, limit)]
        
        if not pdf_files:
            logger.warning("未找到PDF文件")
            return {"processed": 0, "failed": 0, "errors": []}
        
        output_dir.mkdir(parents=True, exist_ok=True)

        # 预过滤：跳过已处理的文件
        filtered_pdf_files: List[Path] = []
        skipped_count = 0
        for pf in pdf_files:
            if self._is_already_processed(pf, output_dir):
                skipped_count += 1
                logger.info(f"跳过已处理文件: {pf.name}")
            else:
                filtered_pdf_files.append(pf)
        if skipped_count:
            logger.info(f"本次批次预先跳过 {skipped_count} 个已处理文件")
        pdf_files = filtered_pdf_files
        
        results = {"processed": 0, "failed": 0, "errors": []}
        batch_start = time.time()
        # 阶段统计缓存
        interval_durations: List[float] = []
        interval_failed = 0
        interval_index = 0
        progress_jsonl_path = self.config.paths.logs_dir / "pdf_progress.jsonl"

        # 从配置读取默认处理选项
        default_output_format = self._get_config_attr('pdf_output_format')
        default_text_only = self._get_config_attr('pdf_text_only_default')
        default_fast = self._get_config_attr('pdf_fast_default')
        default_device = self._get_config_attr('mineru_device') or None
        default_language = self._get_config_attr('mineru_lang')

        max_workers = max(1, self._get_config_attr('pdf_max_workers'))

        def worker(pdf_file: Path):
            file_start = time.time()
            try:
                # GPU内存门控：仅在GPU设备可能被使用时启用
                use_gpu = False
                if torch is not None and torch.cuda.is_available():
                    if default_device is None:
                        use_gpu = True
                    else:
                        use_gpu = ("cuda" in str(default_device).lower())
                if use_gpu:
                    ok = self._wait_for_gpu()
                    if not ok:
                        logger.warning(f"等待GPU空闲超时，{pdf_file.name} 将在CPU上处理")
                        dev_override = "cpu"
                    else:
                        dev_override = default_device
                else:
                    dev_override = default_device

                success = self.process_single_pdf(
                    pdf_file,
                    output_dir,
                    output_format=default_output_format,
                    text_only=default_text_only,
                    device=dev_override,
                    language=default_language,
                    fast=default_fast
                )
                duration = time.time() - file_start
                return (success, pdf_file, duration)
            except Exception as e:
                duration = time.time() - file_start
                logger.error(f"处理文件失败 {pdf_file}: {e}")
                return (False, pdf_file, duration)

        def write_interval_stats():
            interval_count = len(interval_durations)
            total_dur = sum(interval_durations) if interval_durations else 0.0
            throughput = (interval_count / total_dur) if total_dur > 0 else 0.0
            avg_time = (total_dur / interval_count) if interval_count > 0 else 0.0
            fail_rate = (interval_failed / interval_count) if interval_count > 0 else 0.0

            logger.info(
                f"阶段统计[{interval_index+1}]: 共{interval_count}文件 | 吞吐 {throughput:.2f} 文件/秒 | 平均用时 {avg_time:.2f}s/文件 | 失败率 {fail_rate:.1%} | 累计 成功 {results['processed']} 失败 {results['failed']}"
            )

            record = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "stage": "pdf_processing",
                "type": "interval_stats",
                "interval_index": interval_index + 1,
                "interval_size": interval_count,
                "interval_duration_secs": round(total_dur, 3),
                "throughput_files_per_sec": round(throughput, 3),
                "avg_time_per_file_secs": round(avg_time, 3),
                "interval_failed_count": interval_failed,
                "interval_failed_rate": round(fail_rate, 4),
                "cumulative_processed": results["processed"],
                "cumulative_failed": results["failed"],
                "cumulative_failed_rate": round(
                    (results["failed"] / (results["processed"] + results["failed"])) if (results["processed"] + results["failed"]) > 0 else 0.0, 4
                ),
            }
            try:
                with open(progress_jsonl_path, "a", encoding="utf-8") as jf:
                    jf.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as werr:
                logger.warning(f"写入进度JSONL失败: {werr}")

        if max_workers == 1:
            # 保持原有顺序处理与进度体验
            for pdf_file in progress_wrap(pdf_files, desc="PDF处理", unit="file"):
                success, pf, duration = worker(pdf_file)
                interval_durations.append(duration)
                if success:
                    results["processed"] += 1
                    # 写入已处理标记
                    self._write_processed_marker(pf)
                else:
                    results["failed"] += 1
                    results["errors"].append(str(pf))
                    interval_failed += 1

                processed_so_far = results["processed"] + results["failed"]
                if stats_every and processed_so_far > 0 and processed_so_far % max(1, stats_every) == 0:
                    write_interval_stats()
                    interval_durations = []
                    interval_failed = 0
                    interval_index += 1
        else:
            # 并发处理，提升GPU利用率（含显存门控）
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker, f) for f in pdf_files]
                completed = 0
                for fut in as_completed(futures):
                    success, pf, duration = fut.result()
                    interval_durations.append(duration)
                    completed += 1
                    if success:
                        results["processed"] += 1
                        # 写入已处理标记
                        self._write_processed_marker(pf)
                    else:
                        results["failed"] += 1
                        results["errors"].append(str(pf))
                        interval_failed += 1

                    if stats_every and completed % max(1, stats_every) == 0:
                        write_interval_stats()
                        interval_durations = []
                        interval_failed = 0
                        interval_index += 1

        # 处理最后不足一个阶段的剩余统计
        if stats_every and interval_durations:
            write_interval_stats()

        # 写入最终汇总
        batch_duration = time.time() - batch_start
        total_files = results["processed"] + results["failed"]
        overall_throughput = (total_files / batch_duration) if batch_duration > 0 else 0.0
        final_record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "stage": "pdf_processing",
            "type": "final_summary",
            "total_files": total_files,
            "success": results["processed"],
            "failed": results["failed"],
            "overall_duration_secs": round(batch_duration, 3),
            "overall_throughput_files_per_sec": round(overall_throughput, 3),
            "overall_failed_rate": round((results["failed"] / total_files) if total_files > 0 else 0.0, 4),
        }
        try:
            with open(progress_jsonl_path, "a", encoding="utf-8") as jf:
                jf.write(json.dumps(final_record, ensure_ascii=False) + "\n")
        except Exception as werr:
            logger.warning(f"写入进度JSONL失败: {werr}")

        logger.info(f"批处理完成: 成功 {results['processed']}, 失败 {results['failed']}")
        return results