#!/usr/bin/env python3
"""
测试PDF处理器功能
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from core.config import Config
from core.pdf_processor import PDFProcessor
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pdf_processor():
    """测试PDF处理器功能"""
    print("开始测试PDF处理器...")
    
    # 加载配置
    config = Config()
    config.setup_directories()
    
    # 创建PDF处理器实例
    processor = PDFProcessor(config)
    
    # 查找测试PDF文件
    test_input_dir = Path(__file__).parent.parent / 'data' / 'input'
    if not test_input_dir.exists():
        print(f"测试输入目录不存在: {test_input_dir}")
        return False
        
    pdf_files = list(test_input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"未找到PDF文件: {test_input_dir}")
        return False
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    # 设置输出目录
    test_output_dir = Path(__file__).parent.parent / 'data' / 'output'
    test_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 处理第一个PDF文件
    pdf_file = pdf_files[0]
    print(f"处理PDF文件: {pdf_file.name}")
    
    success = processor.process_single_pdf(pdf_file, test_output_dir)
    
    if success:
        print("✅ PDF处理成功!")
        # 检查是否生成了Markdown文件
        md_files = list(test_output_dir.glob("*.md"))
        if md_files:
            print(f"生成了 {len(md_files)} 个Markdown文件")
            for md_file in md_files:
                print(f"  - {md_file.name}")
            return True
        else:
            print("❌ 未生成Markdown文件")
            return False
    else:
        print("❌ PDF处理失败!")
        return False

if __name__ == "__main__":
    print("=== PDF处理器功能测试 ===\n")
    
    success = test_pdf_processor()
    
    if success:
        print("\n🎉 PDF处理器测试完成!")
    else:
        print("\n💥 PDF处理器测试失败!")
        sys.exit(1)