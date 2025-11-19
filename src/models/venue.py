"""
期刊/会议数据模型
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Venue:
    """期刊/会议数据模型"""
    id: str
    venue_name: str
    venue_abbr: Optional[str] = None
    venue_type: str = "journal"  # conference, journal, workshop, symposium
    issn: Optional[str] = None
    publisher: Optional[str] = None
    impact_factor: Optional[float] = None
    ccf_rank: Optional[str] = None  # A, B, C, N
    core_rank: Optional[str] = None
    homepage: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)