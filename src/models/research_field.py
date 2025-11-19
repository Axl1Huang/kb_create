"""
研究领域数据模型
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ResearchField:
    """研究领域数据模型"""
    id: str
    field_name: str
    field_code: Optional[str] = None
    frequency: int = 0
    is_selected: bool = True
    category: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    node_size: int = 50
    display_order: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)