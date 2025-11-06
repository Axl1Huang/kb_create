#!/usr/bin/env python3
"""
简单测试PDF处理器功能
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from core.config import Config
from core.pdf_processor import PDFProcessor

def test_pdf_processor_basic():
    """测试PDF处理器基本功能"""
    print("开始测试PDF处理器基本功能...")
    
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
    
    print(f"✅ 找到 {len(pdf_files)} 个PDF文件")
    print(f"✅ PDF处理器初始化成功")
    print(f"✅ 配置加载成功")
    
    return True

if __name__ == "__main__":
    print("=== PDF处理器基本功能测试 ===\n")
    
    success = test_pdf_processor_basic()
    
    if success:
        print("\n🎉 PDF处理器基本功能测试通过!")
    else:
        print("\n💥 PDF处理器基本功能测试失败!")
        sys.exit(1)