#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
研究领域映射与补全工具：
- 根据 venue、keywords、title、abstract 等上下文，推断并补全 research_field。
- 使用简单的启发式打分机制，优先匹配期刊名中的强信号（如 Chemical Engineering Journal、Marine Pollution Bulletin）。

返回值：字符串（规范化研究领域名）或 None（无法确定）。
"""

from typing import Dict, Any, List, Optional


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def infer_research_field(data: Dict[str, Any]) -> Optional[str]:
    """根据解析出的数据字典推断研究领域。

    期望字段：title, abstract, keywords(list[str]), venue
    """
    title = _norm(data.get("title"))
    abstract = _norm(data.get("abstract"))
    venue = _norm(data.get("venue"))
    kw_list: List[str] = data.get("keywords") or []
    keywords = " ".join([_norm(k) for k in kw_list])

    content = " ".join(filter(None, [title, abstract, keywords, venue]))

    # 强信号：期刊名直接映射（加权更高）
    venue_map = {
        "chemical engineering": "Chemical Engineering",
        "chemical engineering journal": "Chemical Engineering",
        "cej": "Chemical Engineering",
        "marine pollution bulletin": "Marine Pollution",
        "marine pollution": "Marine Pollution",
        "water research": "Environmental Engineering",
        "journal of environmental": "Environmental Engineering",
    }

    for k, v in venue_map.items():
        if k in venue:
            return v

    # 关键词/标题/摘要综合打分
    field_signals = {
        "Chemical Engineering": {
            "chemical engineering", "chem eng", "reaction", "catalysis",
            "adsorption", "oxygen vacancy", "kinetics", "process",
        },
        "Marine Pollution": {
            "marine pollution", "marine", "coastal", "ocean", "sea", "reef",
        },
        "Environmental Engineering": {
            "wastewater", "water quality", "sewage", "hrt", "cod", "bod",
            "bioreactor", "activated sludge", "nitrification", "denitrification",
            "pollutant", "removal", "treatment",
        },
        "Materials Science": {
            "materials", "nanomaterial", "nanomaterials", "sensor", "graphene",
            "lignocellulose", "composite", "adsorbent",
        },
    }

    scores = {f: 0 for f in field_signals.keys()}

    # venue中的弱信号也给予一定加分
    if "chemical" in venue and "engineering" in venue:
        scores["Chemical Engineering"] += 2
    if "marine" in venue and ("pollution" in venue or "bulletin" in venue):
        scores["Marine Pollution"] += 2
    if "water" in venue or "environment" in venue:
        scores["Environmental Engineering"] += 1

    # 内容匹配加分
    for field, tokens in field_signals.items():
        for t in tokens:
            if t in content:
                scores[field] += 1

    # 选择最高分的领域
    best_field = None
    best_score = 0
    for f, s in scores.items():
        if s > best_score:
            best_field = f
            best_score = s

    # 若得分为0则返回None，交由上层决定是否使用兜底
    return best_field if best_score > 0 else None