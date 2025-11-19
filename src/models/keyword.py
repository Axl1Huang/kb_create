"""
关键词数据模型
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Keyword:
    """关键词数据模型"""
    id: str
    keyword_name: str
    field_id: str
    frequency: int = 0
    weight: float = 1.0
    description: Optional[str] = None
    color: Optional[str] = None
    node_size: int = 40
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)