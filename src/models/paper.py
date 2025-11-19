"""
论文数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Paper:
    """论文数据模型"""
    id: str
    title: str
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    venue_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    citations_count: int = 0
    download_count: int = 0
    language: str = "en"
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    node_size: int = 30
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    authors: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """初始化后的处理"""
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.references is None:
            self.references = []
        if self.metadata is None:
            self.metadata = {}