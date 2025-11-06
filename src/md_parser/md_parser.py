#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MD文件解析器
解析MinerU生成的Markdown文件，提取文献信息用于数据库入库
"""

import os
import yaml
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/axlhuang/kb_create/logs/md_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MDParser:
    """MD文件解析器类"""
    
    def __init__(self):
        """初始化解析器"""
        pass
    
    def parse_md_file(self, md_path: str) -> Optional[Dict[str, Any]]:
        """
        解析单个MD文件
        
        Args:
            md_path: MD文件路径
            
        Returns:
            解析后的文献信息字典，如果解析失败返回None
        """
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分离YAML头部和正文
            yaml_content, body_content = self._split_yaml_and_body(content)
            
            # 解析YAML头部
            metadata = self._parse_yaml_header(yaml_content) if yaml_content else {}
            
            # 解析正文内容
            body_data = self._parse_body_content(body_content) if body_content else {}
            
            # 合并数据
            result = {**metadata, **body_data}
            
            # 添加文件路径信息
            result['md_file_path'] = md_path
            
            # 生成唯一ID（使用文件路径的哈希值）
            result['id'] = self._generate_id(md_path)
            
            logger.info(f"成功解析MD文件: {md_path}")
            return result
            
        except Exception as e:
            logger.error(f"解析MD文件失败: {md_path}, 错误: {str(e)}")
            return None
    
    def _split_yaml_and_body(self, content: str) -> tuple:
        """
        分离YAML头部和正文内容
        
        Args:
            content: MD文件完整内容
            
        Returns:
            (yaml_content, body_content) 元组
        """
        lines = content.split('\n')
        
        # 查找YAML块
        if lines[0].strip() == '---':
            # 找到结束标记
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    # YAML部分在第2个---之前
                    yaml_lines = lines[1:i]
                    body_lines = lines[i+1:] if i+1 < len(lines) else []
                    return '\n'.join(yaml_lines), '\n'.join(body_lines)
        
        # 如果没有找到YAML块，认为整个文件都是正文
        return '', content
    
    def _parse_yaml_header(self, yaml_content: str) -> Dict[str, Any]:
        """
        解析YAML头部信息
        
        Args:
            yaml_content: YAML头部内容
            
        Returns:
            解析后的元数据字典
        """
        try:
            metadata = yaml.safe_load(yaml_content)
            if not isinstance(metadata, dict):
                metadata = {}
                
            # 处理作者信息
            if 'authors' in metadata and isinstance(metadata['authors'], list):
                # 转换为简单的作者姓名列表
                authors = []
                for author in metadata['authors']:
                    if isinstance(author, dict) and 'name' in author:
                        authors.append(author['name'])
                    elif isinstance(author, str):
                        authors.append(author)
                metadata['author_names'] = authors
            
            return metadata
        except Exception as e:
            logger.warning(f"解析YAML头部失败: {str(e)}")
            return {}
    
    def _parse_body_content(self, body_content: str) -> Dict[str, Any]:
        """
        解析正文内容，提取标题、摘要等信息
        
        Args:
            body_content: 正文内容
            
        Returns:
            解析后的正文数据字典
        """
        data = {}
        
        # 提取标题（第一个#标题）
        title_match = re.search(r'^#\s+(.+)$', body_content, re.MULTILINE)
        if title_match:
            data['title'] = title_match.group(1).strip()
        
        # 提取章节内容
        sections = self._extract_sections(body_content)
        
        # 从章节中提取有用信息
        if 'Introduction' in sections:
            # 从引言中可能提取研究背景
            pass
            
        if 'Conclusion' in sections or 'Conclusions' in sections:
            # 从结论中可能提取主要发现
            pass
        
        return data
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        提取各个章节内容
        
        Args:
            content: 文档内容
            
        Returns:
            章节名称到内容的映射字典
        """
        sections = {}
        section_pattern = r'^#\s+(.+)$'
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            section_match = re.match(section_pattern, line)
            if section_match:
                # 保存上一个章节
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # 开始新章节
                current_section = section_match.group(1).strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # 保存最后一个章节
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _generate_id(self, file_path: str) -> str:
        """
        根据文件路径生成唯一ID
        
        Args:
            file_path: 文件路径
            
        Returns:
            唯一ID字符串
        """
        import hashlib
        return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def parse_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        解析目录下所有的MD文件
        
        Args:
            directory_path: 目录路径
            
        Returns:
            解析结果列表
        """
        results = []
        directory = Path(directory_path)
        
        # 查找所有MD文件
        md_files = list(directory.rglob("*.md"))
        logger.info(f"找到 {len(md_files)} 个MD文件")
        
        for md_file in md_files:
            result = self.parse_md_file(str(md_file))
            if result:
                results.append(result)
        
        logger.info(f"成功解析 {len(results)} 个MD文件")
        return results
    
    def save_results_to_json(self, results: List[Dict[str, Any]], output_path: str) -> bool:
        """
        将解析结果保存为JSON文件
        
        Args:
            results: 解析结果列表
            output_path: 输出文件路径
            
        Returns:
            保存是否成功
        """
        try:
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存为JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"解析结果已保存到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败: {output_path}, 错误: {str(e)}")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MD文件解析器")
    parser.add_argument("-i", "--input", required=True, help="输入目录或文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出JSON文件路径")
    
    args = parser.parse_args()
    
    # 创建日志目录
    Path("/home/axlhuang/kb_create/logs").mkdir(parents=True, exist_ok=True)
    
    # 创建解析器实例
    parser = MDParser()
    
    # 解析文件或目录
    if os.path.isfile(args.input):
        # 单个文件
        result = parser.parse_md_file(args.input)
        if result:
            parser.save_results_to_json([result], args.output)
        else:
            logger.error("解析失败")
    elif os.path.isdir(args.input):
        # 目录
        results = parser.parse_directory(args.input)
        if results:
            parser.save_results_to_json(results, args.output)
        else:
            logger.error("解析失败")
    else:
        logger.error(f"输入路径不存在: {args.input}")

if __name__ == "__main__":
    main()