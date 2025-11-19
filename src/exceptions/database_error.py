"""
数据库异常类
"""
class DatabaseError(Exception):
    """数据库操作相关的异常"""

    def __init__(self, message: str, query: str = None, params: tuple = None):
        """
        初始化数据库异常

        Args:
            message: 错误消息
            query: SQL查询语句
            params: 查询参数
        """
        super().__init__(message)
        self.message = message
        self.query = query
        self.params = params

    def __str__(self):
        result = self.message
        if self.query:
            result += f"\nQuery: {self.query}"
        if self.params:
            result += f"\nParams: {self.params}"
        return result