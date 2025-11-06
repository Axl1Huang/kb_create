#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
from pathlib import Path

def main():
    # 检查文件是否存在
    sample_file = Path("/home/axlhuang/kb_create/test_output/markdown_only/A-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical.md")
    if not sample_file.exists():
        print("示例文件不存在")
        return
    
    # 读取文件内容
    with open(sample_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("文件读取成功，内容长度:", len(content))
    
    # 创建简化提示词
    prompt = f"""
你是一个专业的学术文献信息提取工具。请从以下学术论文中准确提取信息，并严格按照指定的JSON格式输出。

请从以下Markdown内容中准确提取信息并严格按上述格式输出：

{content[:1000]}... (内容已截断)
"""
    
    # 调用模型
    payload = {
        "model": "qwen3-vl:8b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.95
        }
    }
    
    try:
        print("正在调用LLM模型...")
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        llm_response = result.get("response", "")
        
        print("LLM响应:", llm_response[:200] + "..." if len(llm_response) > 200 else llm_response)
        
        # 保存结果
        output_file = Path("/home/axlhuang/kb_create/test_output/llm_parsed_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(llm_response)
        print(f"解析结果已保存到: {output_file}")
    except Exception as e:
        print(f"调用LLM模型时出错: {e}")

if __name__ == "__main__":
    main()
