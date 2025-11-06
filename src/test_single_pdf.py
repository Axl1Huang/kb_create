#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
from pathlib import Path

def test_single_pdf_processing():
    """
    测试处理单个PDF文件的完整流程
    """
    # 使用实际路径中的一个PDF文件进行测试
    test_pdf = "/mnt/e/大模型文献2025年3月/英文文献/分组1/大于15MB/A-novel-anaerobic-membrane-bioreactor-with-magnetotactic-bacte_2025_Chemical.pdf"
    
    # 检查文件是否存在
    if not os.path.exists(test_pdf):
        print(f"测试文件不存在: {test_pdf}")
        return False
    
    print(f"开始处理测试文件: {test_pdf}")
    
    # 创建测试输出目录
    test_output_dir = Path("/home/axlhuang/kb_create/test_output")
    test_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建MinerU命令，启用表格识别但不启用公式识别
    cmd = [
        "mineru",
        "--path", test_pdf,
        "--output", str(test_output_dir),
        "--method", "txt",
        "--backend", "pipeline",
        "--formula", "False",
        "--table", "True",
        "--device", "cuda"
    ]
    
    print("执行MinerU命令...")
    print(" ".join(cmd))
    
    try:
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("处理成功!")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        
        # 查找生成的Markdown文件
        md_files = list(test_output_dir.rglob("*.md"))
        if md_files:
            # 创建只包含Markdown文件的目录
            md_only_dir = test_output_dir / "markdown_only"
            md_only_dir.mkdir(exist_ok=True)
            
            # 复制Markdown文件到新目录
            for md_file in md_files:
                shutil.copy2(md_file, md_only_dir)
                print(f"已复制Markdown文件: {md_file.name}")
            
            print(f"只保留Markdown文件的目录: {md_only_dir}")
            
            # 删除处理过程中的临时文件和目录
            for item in test_output_dir.iterdir():
                if item.name != "markdown_only":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            print("已删除处理过程中的临时文件和目录")
            
            return True
        else:
            print("未找到生成的Markdown文件")
            return False
    except subprocess.CalledProcessError as e:
        print(f"处理失败: {e}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"处理异常: {e}")
        return False

if __name__ == "__main__":
    test_single_pdf_processing()