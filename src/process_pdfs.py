#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def process_pdfs_with_mineru():
    """
    使用MinerU批量处理PDF文件，仅输出Markdown格式
    """
    # 加载配置文件
    load_dotenv("/home/axlhuang/kb_create/config.env")
    
    # 输入和输出目录
    input_base_dir = Path(os.getenv("INPUT_DIR", "/mnt/e/大模型文献2025年3月/英文文献"))
    output_base_dir = Path(os.getenv("OUTPUT_DIR", "/home/axlhuang/kb_create/output"))
    processed_dir = Path(os.getenv("PROCESSED_DIR", "/home/axlhuang/kb_create/processed"))
    
    # 创建必要的目录
    output_base_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有分组目录
    group_dirs = [d for d in input_base_dir.iterdir() if d.is_dir() and d.name.startswith("分组")]
    
    print(f"找到 {len(group_dirs)} 个分组目录")
    
    # 遍历每个分组目录
    for group_dir in group_dirs:
        print(f"正在处理分组: {group_dir.name}")
        
        # 创建对应的输出目录
        group_output_dir = output_base_dir / group_dir.name
        group_output_dir.mkdir(exist_ok=True)
        
        # 查找该目录下的所有PDF文件
        pdf_files = list(group_dir.glob("*.pdf"))
        print(f"  找到 {len(pdf_files)} 个PDF文件")
        
        # 处理每个PDF文件
        for pdf_file in pdf_files:
            print(f"  正在处理: {pdf_file.name}")
            
            # 构建输出文件路径
            output_file = group_output_dir / f"{pdf_file.stem}.md"
            
            # 检查是否已处理过
            if output_file.exists():
                print(f"    已存在，跳过: {output_file.name}")
                continue
            
            # 构建MinerU命令
            # 使用GPU加速，自动模式，启用公式和表格解析
            cmd = [
                "mineru",
                "--path", str(pdf_file),
                "--output", str(group_output_dir),
                "--method", "auto",
                "--backend", "pipeline",
                "--formula", "True",
                "--table", "True",
                "--device", "cuda"
            ]
            
            try:
                # 执行命令
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(f"    处理成功: {pdf_file.name}")
                
                # 记录已处理的文件
                processed_file = processed_dir / f"{pdf_file.stem}.processed"
                with open(processed_file, "w") as f:
                    f.write(f"Processed: {pdf_file}\n")
                    f.write(f"Output: {output_file}\n")
                    f.write(f"Time: {result.stdout}\n")
                    
            except subprocess.CalledProcessError as e:
                print(f"    处理失败: {pdf_file.name}")
                print(f"    错误信息: {e.stderr}")
            except Exception as e:
                print(f"    处理异常: {pdf_file.name}")
                print(f"    异常信息: {str(e)}")
    
    print("所有PDF文件处理完成")

if __name__ == "__main__":
    process_pdfs_with_mineru()