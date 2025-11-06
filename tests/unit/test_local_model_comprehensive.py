#!/usr/bin/env python3
"""
全面测试本地模型性能和准确性
"""

import sys
import os
import time
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

def test_performance_and_accuracy():
    """测试本地模型的性能和准确性"""
    print("开始全面测试本地模型性能和准确性...")
    
    # 加载配置
    config = Config()
    
    # 创建LLM解析器实例
    parser = LLMParser(config)
    
    # 使用之前处理过的实际论文Markdown内容进行测试
    test_markdown = """# g-Radiolysis of aqueous 2-chloroanisole

## Abstract
The radiation-induced degradation of 2-chloroanisole (2-ClAn) is investigated under various experimental conditions in neutral aqueous media as a function of absorbed radiation dose. The initial yields ( $G _ { \mathrm { i } }$ -values) of substrate degradation as well as those of the resulting major products were determined by HPLC analysis. Probable reaction mechanisms are suggested.

## Authors
Ruth M. Quint, David M. Smith, Jennifer L. Brown

## Keywords
2-Chloroanisole, Radiation degradation, Aqueous solution, HPLC analysis, Reaction mechanisms

## 1. Introduction
The radiolysis of aqueous solutions of 2-chloroanisole has attracted interest due to its relevance in environmental chemistry and radiation chemistry. Understanding the degradation pathways is crucial for assessing the fate of such compounds in aqueous environments under irradiation.

## 2. Experimental
### 2.1 Materials
2-Chloroanisole of high purity was used without further purification. All other chemicals were of analytical grade.

### 2.2 Irradiation Procedure
Solutions were irradiated with a 60Co gamma source at room temperature under air saturation.

## 3. Results and Discussion
### 3.1 Product Analysis
HPLC analysis revealed several degradation products, including phenol derivatives and chloride ions.

### 3.2 Mechanistic Considerations
The degradation likely proceeds through initial OH radical attack on the aromatic ring, followed by subsequent reactions.

## 4. Conclusion
The study provides insights into the radiation-induced degradation of 2-chloroanisole in aqueous solution, contributing to the understanding of radiolytic processes of chlorinated aromatic compounds.

## References
1. Smith, J. et al. (2005). Radiolysis of chlorinated aromatics. J. Phys. Chem. 109, 1234-1245.
2. Brown, A. et al. (2003). Environmental fate of chloroanisoles. Environ. Sci. Technol. 37, 567-573."""

    print("正在使用本地Qwen3-VL 8B模型解析实际论文内容...")
    
    # 记录开始时间
    start_time = time.time()
    
    result = parser.parse_markdown_text(test_markdown)
    
    # 记录结束时间
    end_time = time.time()
    processing_time = end_time - start_time
    
    if result:
        print("✅ 本地模型解析成功!")
        print(f"处理时间: {processing_time:.2f} 秒")
        print(f"标题: {result.get('title')}")
        print(f"作者: {result.get('authors')}")
        print(f"摘要: {result.get('abstract')[:100]}...")
        print(f"关键词: {result.get('keywords')}")
        print(f"年份: {result.get('year')}")
        print(f"期刊: {result.get('venue')}")
        print(f"研究领域: {result.get('research_field')}")
        print(f"DOI: {result.get('doi')}")
        print(f"参考文献数量: {len(result.get('references', []))}")
        
        # 验证关键信息的准确性
        expected_title = "g-Radiolysis of aqueous 2-chloroanisole"
        expected_authors = ["Ruth M. Quint", "David M. Smith", "Jennifer L. Brown"]
        expected_keywords = ["2-Chloroanisole", "Radiation degradation", "Aqueous solution", "HPLC analysis", "Reaction mechanisms"]
        
        accuracy_score = 0
        total_checks = 4
        
        if result.get('title') and expected_title in result.get('title'):
            accuracy_score += 1
            print("✅ 标题准确性: 通过")
        else:
            print("❌ 标题准确性: 未通过")
            
        if result.get('authors') and all(author in result.get('authors') for author in expected_authors):
            accuracy_score += 1
            print("✅ 作者准确性: 通过")
        else:
            print("❌ 作者准确性: 未通过")
            
        if result.get('keywords') and all(keyword in result.get('keywords') for keyword in expected_keywords[:3]):
            accuracy_score += 1
            print("✅ 关键词准确性: 通过")
        else:
            print("❌ 关键词准确性: 未通过")
            
        if result.get('abstract') and len(result.get('abstract')) > 50:
            accuracy_score += 1
            print("✅ 摘要完整性: 通过")
        else:
            print("❌ 摘要完整性: 未通过")
        
        accuracy_percentage = (accuracy_score / total_checks) * 100
        print(f"\n📊 准确性评分: {accuracy_score}/{total_checks} ({accuracy_percentage:.1f}%)")
        print(f"⚡ 处理性能: {processing_time:.2f} 秒")
        
        return True, processing_time, accuracy_percentage
    else:
        print("❌ 本地模型解析失败!")
        return False, processing_time, 0

def compare_with_cloud_model():
    """与云端模型进行对比测试"""
    print("\n开始与云端模型对比测试...")
    
    # 临时切换到云端模型
    os.environ['USE_LOCAL_MODEL'] = 'false'
    
    try:
        config = Config()
        parser = LLMParser(config)
        
        test_markdown = "# Test Paper\n\n## Abstract\nThis is a test abstract for comparison.\n\n## Authors\nTest Author"
        
        start_time = time.time()
        result = parser.parse_markdown_text(test_markdown)
        end_time = time.time()
        cloud_time = end_time - start_time
        
        if result:
            print(f"✅ 云端模型解析成功，耗时: {cloud_time:.2f} 秒")
            os.environ['USE_LOCAL_MODEL'] = 'true'  # 恢复配置
            return True, cloud_time
        else:
            print("❌ 云端模型解析失败")
            os.environ['USE_LOCAL_MODEL'] = 'true'  # 恢复配置
            return False, cloud_time
    except Exception as e:
        print(f"云端模型测试异常: {e}")
        os.environ['USE_LOCAL_MODEL'] = 'true'  # 恢复配置
        return False, 0

if __name__ == "__main__":
    print("=== 本地Qwen3-VL 8B模型全面性能测试 ===\n")
    
    # 测试本地模型
    local_success, local_time, accuracy = test_performance_and_accuracy()
    
    if local_success:
        print("\n✅ 本地模型测试完成!")
        
        # 如果需要，可以取消注释下面的代码来与云端模型对比
        # print("\n" + "="*50)
        # cloud_success, cloud_time = compare_with_cloud_model()
        # 
        # if cloud_success:
        #     speedup = cloud_time / local_time if local_time > 0 else 0
        #     print(f"\n📊 性能对比:")
        #     print(f"   本地模型: {local_time:.2f} 秒")
        #     print(f"   云端模型: {cloud_time:.2f} 秒")
        #     print(f"   性能提升: {speedup:.1f}x" if speedup > 1 else "   本地模型更快")
        
        print(f"\n🎯 最终评估:")
        print(f"   准确性: {accuracy:.1f}%")
        print(f"   处理时间: {local_time:.2f} 秒")
        print(f"   推荐使用: {'✅ 是' if accuracy > 80 else '❌ 否'}")
    else:
        print("\n💥 本地模型测试失败!")
        sys.exit(1)