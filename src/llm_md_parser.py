#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
from pathlib import Path
from typing import Dict, Any

class LLMMdParser:
    """
    使用LLM解析Markdown文件，提取文献信息
    """
    
    def __init__(self, model_name: str = "qwen3-vl:8b", base_url: str = "http://localhost:11434"):
        """
        初始化LLM解析器
        
        Args:
            model_name: Ollama模型名称
            base_url: Ollama服务基础URL
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def _create_prompt(self, md_content: str) -> str:
        """
        创建提示词
        
        Args:
            md_content: Markdown文件内容
            
        Returns:
            构造的提示词
        """
        # 限制MD内容长度以避免超出模型上下文限制
        if len(md_content) > 50000:
            md_content = md_content[:50000] + "\n... (内容已截断) ..."
        
        prompt = f"""
你是一个专业的学术文献信息提取工具。你的任务是从以下Markdown格式的学术论文中准确提取信息，并严格按照指定的JSON格式输出。

重要要求：
1. 必须准确提取文档中的原始信息，不要进行归纳、总结或改写
2. 必须严格按照以下JSON结构输出，不要添加任何其他内容
3. 只返回JSON对象，不要包含任何解释、说明或其他文本
4. 确保所有字段都存在，即使值为空也要保留字段

提取规则：
- paper.title: 必须准确复制文档中第一个#标题的完整内容，不要有任何修改
- paper.abstract: 必须准确复制# A B S T R A C T部分的完整内容
- paper.publication_year: 从文档中提取发表年份，如果找不到则使用2025
- 其他字段按照示例格式填充

严格的输出格式要求：
{{
  "paper": {{
    "id": "根据论文标题生成唯一标识符",
    "title": "必须准确复制文档中第一个#标题的完整内容",
    "abstract": "必须准确复制# A B S T R A C T部分的完整内容",
    "publication_year": "发表年份",
    "venue_id": "chemical_engineering_journal",
    "doi": "10.1016/j.cej.2025.161397",
    "language": "en",
    "node_size": 30
  }},
  "authors": [
    {{
      "id": "作者ID（根据姓名生成）",
      "name": "作者姓名",
      "affiliation": "作者机构"
    }}
  ],
  "research_field": {{
    "id": "water_quality_engineering",
    "field_name": "水处理工程",
    "field_code": "WQE001",
    "category": "环境工程",
    "description": "专注于水处理技术、水质改善和水资源管理的研究领域"
  }},
  "venue": {{
    "id": "chemical_engineering_journal",
    "venue_name": "Chemical Engineering Journal",
    "venue_type": "journal",
    "publisher": "Elsevier",
    "impact_factor": 16.744
  }},
  "keywords": [
    {{
      "id": "关键词ID（根据名称生成）",
      "keyword_name": "关键词名称",
      "field_id": "water_quality_engineering",
      "is_primary": true,
      "relevance_score": 1.0
    }}
  ],
  "hrt_conditions": ["HRT条件列表"],
  "pollutants": ["污染物列表"],
  "enzyme_activities": [
    {{
      "enzyme": "酶名称",
      "activity": "酶活性描述"
    }}
  ],
  "metadata": [
    {{
      "meta_key": "元数据键",
      "meta_value": "元数据值",
      "meta_type": "string"
    }}
  ]
}}

示例输出格式：
{{
  "paper": {{
    "id": "a-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical",
    "title": "A novel anaerobic membrane bioreactor with magnetotactic bacteria for organic sulfur pesticide wastewater treatment: Improvement of enzyme activities, refractory pollutants removal and methane yield",
    "abstract": "The high refractory pollutant and heavy metal content in organic sulfur pesticide wastewater limits the removal of chemical oxygen demand (COD) and methane yield of conventional anaerobic membrane bioreactors (cAnMBRs) due to low enzyme activity. The objective of this study was to investigate the impact of magnetotactic bacteria (MTB) with excellent adsorption capabilities on the performance of the AnMBR system at different hydraulic retention times (HRTs). The MTB-assisted AnMBR (R2) showed improved COD removal efficiency (75 %-78 %) over c-AnMBR (R1) by 3 %-7% at HRT of 60, 48, and 36 h. Mancozeb and ethylenethiourea removal efficiencies of R2 were 7.1 %-25.0 % and 25.2 %-28.5 % higher than R1, respectively. The Mn2+ and Zn2+ of R2 were significantly reduced by 16.8 ± 1.9 % and 10.0 ± 0.8 % than that of R1, which were obtained at HRT of 36 h. The activity ratio of protease and dehydrogenase between R1 and R2 was 205.5 % and 419.6 %, respectively. Specific methane yield and specific methane activity of R2 were 1.16 and 1.13 times those of R1, respectively. A mathematical model correlating refractory pollutants, enzyme activity, and COD removal efficiency was established. This study innovatively developed a green MTB-assisted AnMBR technology that successfully removed refractory pollutants and heavy metals while enhancing enzyme activity and methane yield, reducing toxicity threat and improving energy recovery efficiency, along with providing both scientific basis and technical foundation for low-carbon operation of pesticide wastewater treatment.",
    "publication_year": 2025,
    "venue_id": "chemical_engineering_journal",
    "doi": "10.1016/j.cej.2025.161397",
    "language": "en",
    "node_size": 30
  }},
  "authors": [
    {{
      "id": "shiming_cui",
      "name": "Shiming Cui",
      "affiliation": "Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China"
    }},
    {{
      "id": "dongxue_hu",
      "name": "Dongxue Hu",
      "affiliation": "Key Laboratory of Biotechnology and Bioresources Utilization, Ministry of Education, Dalian Minzu University, 18 Liaohe Road West, Dalian Economic and Technological Development Zone, Dalian 116600, China"
    }}
  ],
  "research_field": {{
    "id": "water_quality_engineering",
    "field_name": "水处理工程",
    "field_code": "WQE001",
    "category": "环境工程",
    "description": "专注于水处理技术、水质改善和水资源管理的研究领域"
  }},
  "venue": {{
    "id": "chemical_engineering_journal",
    "venue_name": "Chemical Engineering Journal",
    "venue_type": "journal",
    "publisher": "Elsevier",
    "impact_factor": 16.744
  }},
  "keywords": [
    {{
      "id": "anaerobic_membrane_bioreactor",
      "keyword_name": "Anaerobic membrane bioreactor (AnMBR)",
      "field_id": "water_quality_engineering",
      "is_primary": true,
      "relevance_score": 1.0
    }},
    {{
      "id": "magnetotactic_bacteria",
      "keyword_name": "Magnetotactic bacteria (MTB)",
      "field_id": "water_quality_engineering",
      "is_primary": true,
      "relevance_score": 0.9
    }}
  ],
  "hrt_conditions": [
    "60 h",
    "48 h",
    "36 h",
    "24 h"
  ],
  "pollutants": [
    "Mancozeb",
    "Ethylenethiourea (ETU)",
    "Mn2+",
    "Zn2+"
  ],
  "enzyme_activities": [
    {{
      "enzyme": "protease",
      "activity": "205.5% higher in R2 vs R1"
    }},
    {{
      "enzyme": "dehydrogenase",
      "activity": "419.6% higher in R2 vs R1"
    }}
  ],
  "metadata": [
    {{
      "meta_key": "cod_removal_efficiency",
      "meta_value": "75-78%",
      "meta_type": "string"
    }},
    {{
      "meta_key": "methane_yield_improvement",
      "meta_value": "1.16 times higher in R2 vs R1",
      "meta_type": "string"
    }}
  ]
}}

请从以下Markdown内容中准确提取信息并严格按上述格式输出：
{md_content}

再次强调：必须准确提取原始信息，不要进行归纳或改写，严格按照指定的JSON格式输出，不要包含任何解释或其他文本。
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM模型
        
        Args:
            prompt: 提示词
            
        Returns:
            模型响应
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,  # 最低随机性以获得更一致的结果
                "top_p": 0.95
            }
        }
        
        try:
            print("正在调用LLM模型...")
            response = requests.post(self.api_url, json=payload, timeout=300)  # 5分钟超时
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.Timeout:
            print("LLM模型调用超时")
            return ""
        except Exception as e:
            print(f"调用LLM模型时出错: {e}")
            return ""
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM返回的JSON响应
        
        Args:
            response: LLM返回的响应文本
            
        Returns:
            解析后的字典数据
        """
        if not response:
            print("响应为空")
            return {}
        
        # 清理响应，移除可能的代码块标记
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # 移除开头的```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]  # 移除开头的```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # 移除结尾的```
        cleaned_response = cleaned_response.strip()
        
        # 如果响应本身就是有效的JSON格式
        try:
            # 尝试直接解析JSON
            result = json.loads(cleaned_response)
            print("直接解析JSON成功")
            return result
        except json.JSONDecodeError:
            pass
        
        # 尝试从响应中提取JSON
        try:
            # 查找第一个{和最后一个}之间的内容
            start = cleaned_response.find('{')
            end = cleaned_response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = cleaned_response[start:end]
                # 清理JSON字符串中的特殊字符，但保留必要的结构
                # 只移除首尾的空白字符，保留内部的格式
                json_str = json_str.strip()
                
                # 尝试解析提取的JSON
                result = json.loads(json_str)
                print("从响应中提取JSON成功")
                return result
            else:
                print("无法从响应中提取JSON - 未找到有效的JSON结构")
                print(f"响应内容: {cleaned_response[:200]}...")
                return {}
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"提取的JSON字符串: {json_str[:200]}...")
            return {}
        except Exception as e:
            print(f"解析JSON响应时出错: {e}")
            print(f"响应内容: {cleaned_response[:200]}...")
            return {}
    
    def parse_md_file(self, file_path: Path) -> Dict[str, Any]:
        """
        解析单个MD文件
        
        Args:
            file_path: MD文件路径
            
        Returns:
            解析后的文献信息字典
        """
        try:
            print(f"正在读取文件: {file_path}")
            # 读取MD文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            print("正在创建提示词...")
            # 创建提示词
            prompt = self._create_prompt(md_content)
            
            print("正在调用LLM模型...")
            # 调用LLM模型
            response = self._call_llm(prompt)
            
            if not response:
                print("LLM模型返回空响应")
                return {}
            
            print("正在解析响应...")
            # 解析响应
            result = self._parse_json_response(response)
            
            return result
        except Exception as e:
            print(f"解析文件 {file_path} 时出错: {e}")
            return {}
    
    def parse_directory(self, directory_path: Path) -> list:
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
                if paper_info:
                    papers.append(paper_info)
            except Exception as e:
                print(f"解析文件 {md_file} 时出错: {e}")
        
        return papers

def main():
    """
    主函数，用于测试LLM MD解析器
    """
    # 创建解析器实例
    parser = LLMMdParser()
    
    # 解析示例文件
    sample_file = Path("/home/axlhuang/kb_create/test_output/markdown_only/A-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical.md")
    if sample_file.exists():
        print("开始解析MD文件...")
        paper_info = parser.parse_md_file(sample_file)
        
        if paper_info:
            print("解析结果:")
            print(json.dumps(paper_info, ensure_ascii=False, indent=2))
            
            # 保存结果到文件
            output_file = Path("/home/axlhuang/kb_create/test_output/llm_parsed_result.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(paper_info, f, ensure_ascii=False, indent=2)
            print(f"解析结果已保存到: {output_file}")
        else:
            print("解析失败")
    else:
        print("示例文件不存在")

if __name__ == "__main__":
    main()