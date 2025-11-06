import requests
import json

def test_local_model_with_real_paper():
    # 读取实际的学术论文Markdown文件
    file_path = "/home/axlhuang/kb_create/tests/data/md/--Radiolysis-of-aqueous-2-chloroanisole_2006_Radiation-Physics-and-Chemistry.md"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        print(f"成功读取文件: {file_path}")
        print(f"文件大小: {len(markdown_text)} 字符")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 移除字符长度限制，使用完整文本进行测试
    print(f"使用完整文本进行测试，文本长度: {len(markdown_text)} 字符")
    
    # 构造与LLM解析器一致的提示词
    instruction = (
        "你是一名面向学术论文的结构化信息抽取助手。"
        "请从以下Markdown文本中提取论文的核心元数据，并以严格的JSON格式输出，不要包含任何多余文字。\n\n"
        "必须输出的字段：\n"
        "- title: string\n"
        "- authors: string数组（作者姓名列表）\n"
        "- abstract: string\n"
        "- keywords: string数组\n"
        "- year: number 或 null\n"
        "- venue: string 或 null（期刊或会议名）\n"
        "- research_field: string 或 null（研究领域简述）\n"
        "- doi: string 或 null\n"
        "- references: string数组（参考文献条目，若无则空数组）\n\n"
        "注意：\n"
        "- 如果无法确定某字段，请使用 null 或空数组\n"
        "- 严格输出可解析的JSON，键名使用上面的英文\n"
        "- 输出必须是严格的JSON格式，使用双引号包围字符串，不要包含任何解释性文字\n"
        "- 不要包含任何Markdown格式、代码块标记（如```json）或额外说明\n"
        "- 确保输出的JSON可以直接被Python的json.loads()函数解析\n"
        "- 所有字符串值必须使用双引号，不能使用单引号\n"
        "- 不要在JSON中包含任何注释\n"
        "- 重要：只输出JSON，不要输出任何其他内容，包括解释、说明、分析等\n"
        "- 重要：不要输出任何前缀或后缀，直接输出JSON对象\n"
        "- 输出格式示例：{\"title\": \"论文标题\", \"authors\": [\"作者1\", \"作者2\"], \"abstract\": \"摘要内容\", \"keywords\": [\"关键词1\", \"关键词2\"], \"year\": 2024, \"venue\": \"期刊名称\", \"research_field\": \"研究领域\", \"doi\": \"DOI编号\", \"references\": [\"参考文献1\", \"参考文献2\"]}\n"
        "- 再次强调：只输出JSON，不要包含任何其他文字！\n"
    )
    
    prompt = f"{instruction}\n\n<MARKDOWN>\n{markdown_text}\n</MARKDOWN>"
    
    # 构建消息格式
    messages = [
        {"role": "system", "content": "你是严谨的学术信息抽取助手。你的任务是严格按照要求输出JSON格式，不要包含任何解释性文字、注释或额外信息。输出必须是可直接解析的JSON格式，使用双引号包围所有字符串，不要使用单引号。确保JSON格式正确，不要包含任何语法错误。重要：只输出JSON，不要输出任何其他内容，包括解释、说明、分析等。不要使用Markdown代码块标记（如```json）。输出的内容必须能够被Python的json.loads()函数直接解析。"},
        {"role": "user", "content": prompt},
    ]
    
    # 构建请求数据
    data = {
        "model": "qwen3-vl:8b",
        "messages": messages,
        "stream": False,
        "temperature": 0.2
    }
    
    print("调用本地Qwen3-VL 8B模型")
    print(f"发送提示词长度: {len(prompt)} 字符")
    
    try:
        # 调用本地Ollama API
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=data,
            timeout=120
        )
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            content = result.get('message', {}).get('content', '')
            print("本地模型调用成功")
            print("返回内容:")
            print(content)
            
            # 尝试解析JSON
            try:
                parsed_json = json.loads(content)
                print("\nJSON解析成功!")
                print(f"标题: {parsed_json.get('title')}")
                print(f"作者: {parsed_json.get('authors')}")
                print(f"摘要长度: {len(parsed_json.get('abstract', ''))} 字符")
                print(f"关键词: {parsed_json.get('keywords')}")
                print(f"年份: {parsed_json.get('year')}")
                print(f"期刊: {parsed_json.get('venue')}")
                print(f"研究领域: {parsed_json.get('research_field')}")
                print(f"参考文献数量: {len(parsed_json.get('references', []))}")
                
                # 保存结果到文件
                output_file = "/home/axlhuang/kb_create/tests/output/parsed_data/real_paper_test_result.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(parsed_json, f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存到: {output_file}")
            except json.JSONDecodeError as e:
                print(f"\nJSON解析失败: {e}")
                # 保存原始输出到文件
                output_file = "/home/axlhuang/kb_create/tests/output/parsed_data/real_paper_test_raw.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"原始输出已保存到: {output_file}")
                
            return content
        else:
            print(f"本地模型调用失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"本地模型请求失败: {e}")
        return None

if __name__ == "__main__":
    test_local_model_with_real_paper()
