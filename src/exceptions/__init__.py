"""
自定义异常模块
"""
from .processing_error import ProcessingError
from .database_error import DatabaseError

__all__ = [
    "ProcessingError",
    "DatabaseError"
]