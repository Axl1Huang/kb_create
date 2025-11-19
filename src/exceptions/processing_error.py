"""
处理异常类
"""
class ProcessingError(Exception):
    """处理过程中发生的异常"""

    def __init__(self, message: str, details: dict = None):
        """
        初始化处理异常

        Args:
            message: 错误消息
            details: 详细信息
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message