#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
from pathlib import Path
from typing import Dict, List, Any

class MDParser:
    """
    解析MinerU生成的Markdown文件，提取文献信息
    """
    
    def __init__(self):
        # 为实际的MinerU输出格式定义模式
        self.patterns = {
            'keywords': r'Keywords:\s*\n(.*?)(?=\n#|\Z)',
            'references': r'# References\s*\n(.*?)(?=\n#|\Z)'
        }
    
    def parse_md_file(self, file_path: Path) -> Dict[str, Any]:
        """
        解析单个MD文件，提取文献信息
        
        Args:
            file_path: MD文件路径
            
        Returns:
            包含文献信息的字典
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取各部分信息
        paper_info = {
            'title': self._extract_title_from_first_header(content),
            'abstract': self._extract_abstract(content),
            'authors': self._extract_authors_from_header(content),
            'year': self._extract_year_from_content(content),
            'venue': self._extract_venue_from_content(content),
            'keywords': self._extract_keywords(content),
            'references': self._extract_references(content),
            'cod_removal_efficiency': self._extract_cod_removal_efficiency(content),
            'hrt_conditions': self._extract_hrt_conditions(content),
            'pollutants_studied': self._extract_pollutants_studied(content),
            'file_name': file_path.name
        }
        
        return paper_info
    
    def _extract_title_from_first_header(self, content: str) -> str:
        """从第一个#标题提取标题"""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        return match.group(1).strip() if match else ""
    
    def _extract_abstract(self, content: str) -> str:
        """提取摘要部分"""
        # 查找# A B S T R A C T部分后的文本直到下一个标题
        match = re.search(r'# A B S T R A C T\s*\n(.*?)(?=\n#|\Z)', content, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _extract_authors_from_header(self, content: str) -> List[Dict[str, str]]:
        """从标题下方提取作者信息"""
        lines = content.split('\n')
        title_line_idx = -1
        
        # 找到第一个标题的位置
        for i, line in enumerate(lines):
            if line.strip().startswith('# ') and not line.strip().startswith('# A'):
                title_line_idx = i
                break
        
        # 提取标题后的作者行
        authors = []
        if title_line_idx >= 0:
            # 获取标题后的几行，直到遇到Keywords或其他标题
            i = title_line_idx + 1
            while i < len(lines) and i < title_line_idx + 20:  # 最多检查20行
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                    
                # 如果遇到Keywords或其他标题，停止
                if line.startswith('Keywords') or line.startswith('#'):
                    break
                    
                # 如果行中包含逗号和机构相关信息，可能是作者和机构
                if ',' in line and ('University' in line or 'Laboratory' in line or 'College' in line):
                    # 尝试分离作者和机构
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        author_name = parts[0].strip()
                        affiliation = line.strip()
                        authors.append({
                            'name': author_name,
                            'affiliation': affiliation
                        })
                elif line and not line.startswith('#'):
                    # 如果看起来像作者姓名的格式
                    if re.match(r'^[A-Za-z\s\.,]+$', line) and len(line.split()) >= 2:
                        authors.append({
                            'name': line,
                            'affiliation': ''
                        })
                
                i += 1
        
        return authors
    
    def _extract_year_from_content(self, content: str) -> int:
        """从内容中提取年份"""
        # 查找类似年份的数字（如2025）
        years = re.findall(r'\b(19|20)\d{2}\b', content)
        for year in years:
            year_int = int(year)
            if 1900 <= year_int <= 2030:  # 合理的年份范围
                return year_int
        return 0
    
    def _extract_venue_from_content(self, content: str) -> str:
        """从内容中提取期刊/会议信息"""
        # 在实际文件中可能没有明确的期刊信息，但可以根据内容推断
        if 'Chemical' in content and 'Engineering' in content:
            return "Chemical Engineering Journal"
        return ""
    
    def _extract_cod_removal_efficiency(self, content: str) -> str:
        """提取COD去除效率信息"""
        # 查找COD去除效率的相关信息
        match = re.search(r'COD removal efficiency.*?(\d+\s*%?\s*-?\s*\d*%?)', content, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _extract_hrt_conditions(self, content: str) -> List[str]:
        """提取HRT条件信息"""
        # 查找HRT相关的信息
        hrt_list = []
        hrt_matches = re.findall(r'HRT\s*(?:of\s*)?(\d+\s*h)', content, re.IGNORECASE)
        for match in hrt_matches:
            hrt_list.append(match.strip())
        return list(set(hrt_list))  # 去重
    
    def _extract_pollutants_studied(self, content: str) -> List[str]:
        """提取研究的污染物信息"""
        pollutants = []
        # 查找常见的污染物名称
        pollutant_keywords = ['Mancozeb', 'Ethylenethiourea', 'ETU', 'Mn2\+', 'Zn2\+', 'COD']
        for keyword in pollutant_keywords:
            if re.search(keyword, content, re.IGNORECASE):
                # 特殊处理一些关键词
                if keyword == 'Mn2\+':
                    pollutants.append('Mn2+')
                elif keyword == 'Zn2\+':
                    pollutants.append('Zn2+')
                else:
                    pollutants.append(keyword)
        return list(set(pollutants))  # 去重
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        match = re.search(self.patterns['keywords'], content, re.DOTALL)
        if not match:
            return []
        
        keywords_text = match.group(1).strip()
        # 按行分割并清理关键词
        keywords = []
        for line in keywords_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                keywords.append(line)
        return keywords
    
    def _extract_references(self, content: str) -> List[Dict[str, str]]:
        """提取参考文献"""
        match = re.search(self.patterns['references'], content, re.DOTALL)
        if not match:
            return []
        
        references_text = match.group(1).strip()
        references = []
        
        # 解析参考文献行
        for line in references_text.split('\n'):
            line = line.strip()
            if line and re.match(r'\[\d+\]', line):  # 匹配方括号编号的参考文献
                # 简单解析参考文献格式
                ref_match = re.match(r'\[\d+\]\s*(.*)', line)
                if ref_match:
                    reference = ref_match.group(1).strip()
                    references.append({
                        'citation': reference
                    })
        
        return references
    
    def parse_directory(self, directory_path: Path) -> List[Dict[str, Any]]:
        """
        解析目录下所有MD文件
        
        Args:
            directory_path: 包含MD文件的目录路径
            
        Returns:
            文献信息列表
        """
        papers = []
        md_files = directory_path.glob("*.md")
        
        for md_file in md_files:
            try:
                paper_info = self.parse_md_file(md_file)
                papers.append(paper_info)
            except Exception as e:
                print(f"解析文件 {md_file} 时出错: {e}")
        
        return papers

def main():
    """
    主函数，用于测试MD解析器
    """
    # 创建解析器实例
    parser = MDParser()
    
    # 解析实际文件
    actual_file = Path("/home/axlhuang/kb_create/test_output/markdown_only/A-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical.md")
    if actual_file.exists():
        paper_info = parser.parse_md_file(actual_file)
        print("解析结果:")
        print(json.dumps(paper_info, ensure_ascii=False, indent=2))
    
    # 解析整个目录
    sample_dir = Path("/home/axlhuang/kb_create/test_output/markdown_only")
    papers = parser.parse_directory(sample_dir)
    print(f"\n共解析 {len(papers)} 篇文献")

if __name__ == "__main__":
    main()