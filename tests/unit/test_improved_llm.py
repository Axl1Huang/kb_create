#!/usr/bin/env python3
"""
测试改进后的LLM解析器
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.config import Config
from src.core.llm_parser import LLMParser
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_llm_parser():
    """测试LLM解析器"""
    print("开始测试改进后的LLM解析器...")
    
    # 加载配置
    config = Config()
    
    # 创建LLM解析器实例
    parser = LLMParser(config)
    
    # 测试用的简单Markdown文本
    test_markdown = """
# 测试论文标题

## 摘要
这是一个测试用的论文摘要，用于验证LLM解析器的功能。

## 作者
张三, 李四, 王五

## 关键词
测试, 验证, LLM解析

## 引言
这是引言部分的内容。

## 结论
这是结论部分的内容。
"""
    
    print("正在解析测试Markdown文本...")
    result = parser.parse_markdown_text(test_markdown)
    
    if result:
        print("✅ LLM解析成功!")
        print(f"标题: {result.get('title')}")
        print(f"作者: {result.get('authors')}")
        print(f"摘要: {result.get('abstract')}")
        print(f"关键词: {result.get('keywords')}")
        return True
    else:
        print("❌ LLM解析失败!")
        return False

if __name__ == "__main__":
    success = test_llm_parser()
    if success:
        print("\n🎉 LLM解析器测试完成!")
    else:
        print("\n💥 LLM解析器测试失败!")
        sys.exit(1)