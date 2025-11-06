import logging
import shutil
from pathlib import Path
from typing import List, Optional

def cleanup_temp_files(temp_dir: Path):
    """清理临时文件"""
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

def find_files_by_extension(directory: Path, extension: str) -> List[Path]:
    """按扩展名查找文件"""
    return list(directory.rglob(f"*{extension}"))

def ensure_directory(path: Path) -> Path:
    """确保目录存在，不存在则创建"""
    path.mkdir(parents=True, exist_ok=True)
    return path

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def get_file_info(file_path: Path) -> dict:
    """获取文件信息"""
    stat = file_path.stat()
    return {
        "name": file_path.name,
        "size": format_file_size(stat.st_size),
        "modified": stat.st_mtime,
        "path": str(file_path)
    }