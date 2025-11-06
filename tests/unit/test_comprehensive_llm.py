#!/usr/bin/env python3
"""
全面测试改进后的LLM解析器
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

def test_llm_parser_comprehensive():
    """全面测试LLM解析器"""
    print("开始全面测试改进后的LLM解析器...")
    
    # 加载配置
    config = Config()
    
    # 创建LLM解析器实例
    parser = LLMParser(config)
    
    # 测试用的更复杂的Markdown文本
    test_markdown = """
# A Novel Anaerobic Membrane Bioreactor with Magnetotactic Bacteria for Enhanced Wastewater Treatment

## Abstract
This study presents a novel anaerobic membrane bioreactor (AnMBR) system integrated with magnetotactic bacteria (MTB) for enhanced wastewater treatment. The system demonstrates improved organic removal efficiency and membrane fouling mitigation through magnetic manipulation of bacterial aggregates. Experimental results show 95% COD removal efficiency and 40% reduction in membrane fouling rate compared to conventional AnMBR systems.

## Authors
Shiming Cui, Dongxue Hu, Zhaobo Chen

## Keywords
anaerobic membrane bioreactor, magnetotactic bacteria, organic sulfur pesticide, membrane fouling, wastewater treatment

## 1. Introduction
Anaerobic membrane bioreactors have gained significant attention in recent years for their ability to achieve high organic removal rates while producing less sludge compared to aerobic systems. However, membrane fouling remains a major challenge limiting their widespread application. The integration of magnetotactic bacteria offers a promising solution to this problem through magnetic field manipulation.

## 2. Materials and Methods
### 2.1 Reactor Configuration
The AnMBR system was configured with a 5L working volume and ceramic membrane modules with 0.1μm pore size.

### 2.2 Magnetotactic Bacteria Enrichment
MTB were enriched from freshwater sediments using magnetic separation techniques.

### 2.3 Operating Conditions
The reactor was operated at 35°C with a hydraulic retention time of 8 hours.

## 3. Results and Discussion
### 3.1 Organic Removal Performance
The system achieved an average COD removal efficiency of 95%, with effluent COD concentrations consistently below 50 mg/L.

### 3.2 Membrane Fouling Analysis
Application of magnetic fields reduced membrane fouling rate by 40% compared to control conditions.

## 4. Conclusion
The integration of magnetotactic bacteria in AnMBR systems represents a significant advancement in membrane bioreactor technology, offering improved performance and operational stability.

## References
1. Smith, J. et al. (2020). Advanced membrane bioreactor technologies. Water Research, 45(3), 123-135.
2. Johnson, A. et al. (2019). Magnetotactic bacteria in environmental applications. Environmental Science & Technology, 53(12), 6789-6798.
"""
    
    print("正在解析复杂的Markdown文本...")
    result = parser.parse_markdown_text(test_markdown)
    
    if result:
        print("✅ LLM解析成功!")
        print(f"标题: {result.get('title')}")
        print(f"作者: {result.get('authors')}")
        print(f"摘要: {result.get('abstract')[:100]}...")
        print(f"关键词: {result.get('keywords')}")
        print(f"年份: {result.get('year')}")
        print(f"期刊: {result.get('venue')}")
        print(f"研究领域: {result.get('research_field')}")
        print(f"DOI: {result.get('doi')}")
        print(f"参考文献数量: {len(result.get('references', []))}")
        return True
    else:
        print("❌ LLM解析失败!")
        return False

if __name__ == "__main__":
    success = test_llm_parser_comprehensive()
    if success:
        print("\n🎉 全面测试完成!")
    else:
        print("\n💥 全面测试失败!")
        sys.exit(1)