"""
作者数据模型
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Author:
    """作者数据模型"""
    id: str
    author_name: str
    author_name_en: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None
    homepage: Optional[str] = None
    h_index: int = 0
    total_citations: int = 0
    research_interests: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)