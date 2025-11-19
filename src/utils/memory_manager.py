"""
内存管理优化模块
"""
import gc
import psutil
import logging
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)

class MemoryManager:
    """内存管理器"""

    def __init__(self, config=None):
        self.config = config
        self.memory_lock = Lock()
        self.last_gc_time = 0

    def get_memory_info(self):
        """获取内存信息"""
        memory = psutil.virtual_memory()
        return {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "percent": memory.percent
        }

    def should_trigger_gc(self, threshold_percent: float = 80.0) -> bool:
        """检查是否应该触发垃圾回收"""
        memory_info = self.get_memory_info()
        return memory_info["percent"] > threshold_percent

    def optimize_memory(self, force: bool = False, threshold_percent: float = 80.0):
        """优化内存使用"""
        with self.memory_lock:
            if force or self.should_trigger_gc(threshold_percent):
                # 执行垃圾回收
                collected = gc.collect()
                logger.info(f"执行垃圾回收，回收了 {collected} 个对象")

                # 清理循环引用
                gc.collect()

                # 获取清理后的内存信息
                memory_info = self.get_memory_info()
                logger.info(f"内存使用情况: {memory_info['used_gb']:.2f}GB / {memory_info['total_gb']:.2f}GB ({memory_info['percent']:.1f}%)")

    def get_optimal_worker_count(self, base_workers: int = 4) -> int:
        """根据内存情况动态调整工作线程数"""
        memory_info = self.get_memory_info()

        # 如果内存使用率超过90%，减少工作线程数
        if memory_info["percent"] > 90:
            return max(1, base_workers // 2)
        # 如果内存使用率超过80%，保持工作线程数
        elif memory_info["percent"] > 80:
            return base_workers
        # 如果内存充足，可以增加工作线程数
        else:
            return min(base_workers * 2, 16)  # 最多16个线程

# 全局内存管理器实例
memory_manager = MemoryManager()