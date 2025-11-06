#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从指定Markdown文件生成示例JSON数据，字段对齐导入器期望结构：
- 基本信息：title, abstract, year, venue, doi, pdf_path
- 关联信息：authors(list), keywords(list), research_field
- 元数据：paper_metadata中的 references(list)

用法：
  python scripts/generate_sample_json_from_md.py \
    --md /path/to/file.md \
    --out /path/to/output.json
"""

import re
import json
import argparse
from pathlib import Path


def extract_title(text: str) -> str:
    # 第一行以# 开头的标题
    m = re.search(r"^#\s+(.*)", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_authors(text: str) -> list:
    # 标题下一行通常为作者列表
    lines = text.splitlines()
    # 找到标题行索引
    title_idx = None
    for i, line in enumerate(lines[:10]):
        if line.strip().startswith('# '):
            title_idx = i
            break
    if title_idx is None:
        return []
    # 作者行通常在标题下一行
    for j in range(title_idx + 1, min(title_idx + 5, len(lines))):
        line = lines[j].strip()
        if line and not line.startswith('#'):
            # 去除脚注标记如 a,b 等以及多余空格
            cleaned = re.sub(r"\s*[\^\*⁎]+", "", line)
            # 以逗号分割并清理
            parts = [p.strip() for p in cleaned.split(',') if p.strip()]
            # 过滤机构信息（包含大学、系、Italy等）
            parts = [p for p in parts if not re.search(r"(Universit|University|Dipartimento|Italy|Greece|Cyprus|Rome|PA)", p, re.IGNORECASE)]
            # 简单姓名过滤：包含空格且无数字
            authors = [p for p in parts if re.search(r"[A-Za-z]", p) and not re.search(r"\d", p)]
            return authors
    return []


def extract_section(text: str, header: str) -> str:
    # 提取以# header为标题的段落，直到下一个# 开头标题
    pattern = rf"^#\s*{re.escape(header)}\s*$"
    m = re.search(pattern, text, re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    # 找到下一个标题位置
    next_m = re.search(r"^#\s+", text[start:], re.MULTILINE)
    end = start + next_m.start() if next_m else len(text)
    return text[start:end].strip()


def extract_abstract(text: str) -> str:
    abs_text = extract_section(text, "A B S T R A C T")
    # 抽取段落首段
    if abs_text:
        # 去掉行内公式符号
        cleaned = re.sub(r"\$[^$]*\$", "", abs_text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
    return ""


def extract_keywords(text: str) -> list:
    m = re.search(r"^\s*Keywords\s*:\s*(.+)$", text, re.MULTILINE)
    if not m:
        return []
    line = m.group(1).strip()
    # 先按空格拆分，再特殊合并已知短语
    tokens = [t for t in re.split(r"\s+", line) if t]
    joined = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if i + 1 < len(tokens) and (t.lower() == 'stable' and tokens[i + 1].lower() == 'isotopes'):
            joined.append('Stable isotopes')
            i += 2
        else:
            joined.append(t.rstrip(',').strip())
            i += 1
    # 清理末尾逗号并去重、去空
    cleaned = []
    for k in joined:
        k = k.strip(',').strip()
        if k:
            cleaned.append(k)
    # 将单词表恢复常见短语
    # 组合："Marine" "Pollution" -> "Marine Pollution" 若存在
    # 此处不强制组合，保留原始抽取
    # 特定大小写修正
    return cleaned


def extract_doi(text: str) -> str:
    m = re.search(r"10\.\d{4,9}/\S+", text)
    return m.group(0).strip().rstrip('.') if m else ""


def infer_venue_from_doi(doi: str) -> str:
    if 'j.marpolbul' in doi:
        return 'Marine Pollution Bulletin'
    return ''


def extract_year_from_doi(doi: str) -> int:
    m = re.search(r"/([12][0-9]{3})[\./]", doi)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def extract_references(text: str) -> list:
    # 从References开始直到文件结束，按行聚合为简单字符串列表
    m = re.search(r"^#\s*References\s*$", text, re.MULTILINE)
    if not m:
        return []
    start = m.end()
    refs_text = text[start:].strip()
    # 去掉图片段落与空行
    lines = [ln.strip() for ln in refs_text.splitlines() if ln.strip() and not ln.strip().startswith('![')]
    # 按句号分割可能过度，保留整行
    # 返回前20行引用作为示例
    return lines[:20]


def build_sample(json_path: Path, md_path: Path) -> dict:
    text = md_path.read_text(encoding='utf-8', errors='ignore')
    title = extract_title(text)
    authors = extract_authors(text)
    abstract = extract_abstract(text)
    keywords = extract_keywords(text)
    doi = extract_doi(text)
    venue = infer_venue_from_doi(doi)
    year = extract_year_from_doi(doi)
    references = extract_references(text)

    data = {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "keywords": keywords,
        "doi": doi or None,
        "venue": venue or None,
        "year": year,
        "pdf_path": str(md_path),
        "research_field": "Marine Pollution",  # 基于内容与期刊推断
        # 供导入器作为paper_metadata的字段（如需）
        "references": references,
        # 其他可能的占位字段（暂无则不填）
        # "hrt_conditions": None,
        # "pollutants": None,
        # "cod_removal_efficiency": None,
        # "enzyme_activities": None,
    }

    # 写入文件
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description="从Markdown生成示例JSON")
    parser.add_argument("--md", type=Path, required=True, help="输入Markdown文件路径")
    parser.add_argument("--out", type=Path, required=True, help="输出JSON文件路径")
    args = parser.parse_args()

    data = build_sample(args.out, args.md)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()