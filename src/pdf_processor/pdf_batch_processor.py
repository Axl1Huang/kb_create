#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF批量处理脚本
使用MinerU处理指定目录下的所有PDF文件，生成Markdown输出
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import List
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/axlhuang/kb_create/logs/pdf_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# MinerU命令路径
MINERU_CMD = "/home/axlhuang/miniconda3/envs/mineru/bin/mineru"

def get_pdf_files(root_dir: str) -> List[str]:
    """
    获取指定目录下所有的PDF文件路径
    
    Args:
        root_dir: 根目录路径
        
    Returns:
        PDF文件路径列表
    """
    pdf_files = []
    root_path = Path(root_dir)
    
    # 遍历所有子目录，查找PDF文件
    for pdf_file in root_path.rglob("*.pdf"):
        # 排除"过程文件"目录
        if "过程文件" not in str(pdf_file):
            pdf_files.append(str(pdf_file))
            
    logger.info(f"找到 {len(pdf_files)} 个PDF文件")
    return pdf_files

def process_single_pdf(pdf_path: str, output_dir: str) -> bool:
    """
    处理单个PDF文件
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录路径
        
    Returns:
        处理是否成功
    """
    try:
        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 构建命令
        cmd = [
            MINERU_CMD,
            "-p", pdf_path,
            "-o", output_dir,
            "-m", "auto",  # 自动选择方法
            "-b", "pipeline"  # 使用pipeline后端
        ]
        
        logger.info(f"正在处理: {pdf_path}")
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"成功处理: {pdf_path}")
            return True
        else:
            logger.error(f"处理失败: {pdf_path}, 错误: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"处理超时: {pdf_path}")
        return False
    except Exception as e:
        logger.error(f"处理出错: {pdf_path}, 错误: {str(e)}")
        return False

def process_pdfs_batch(input_dir: str, output_dir: str, max_workers: int = 4) -> None:
    """
    批量处理PDF文件
    
    Args:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
        max_workers: 最大并发处理数
    """
    logger.info(f"开始批量处理PDF文件")
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    
    # 获取所有PDF文件
    pdf_files = get_pdf_files(input_dir)
    
    if not pdf_files:
        logger.warning("未找到任何PDF文件")
        return
    
    # 处理每个PDF文件，每10个文件显示一次进度
    success_count = 0
    fail_count = 0
    total_files = len(pdf_files)
    
    for i, pdf_file in enumerate(pdf_files):
        # 每10个文件显示一次进度
        if (i + 1) % 10 == 0 or (i + 1) == total_files:
            logger.info(f"进度: {i+1}/{total_files} ({(i+1)/total_files*100:.1f}%)")
        
        # 生成对应的输出目录结构，保持与原目录结构一致
        relative_path = os.path.relpath(pdf_file, input_dir)
        output_subdir = os.path.join(output_dir, os.path.dirname(relative_path))
        
        if process_single_pdf(pdf_file, output_subdir):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"批量处理完成. 成功: {success_count}, 失败: {fail_count}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PDF批量处理器")
    parser.add_argument("-i", "--input", required=True, help="输入目录路径")
    parser.add_argument("-o", "--output", required=True, help="输出目录路径")
    parser.add_argument("-w", "--workers", type=int, default=4, help="最大并发处理数")
    
    args = parser.parse_args()
    
    # 检查输入目录是否存在
    if not os.path.exists(args.input):
        logger.error(f"输入目录不存在: {args.input}")
        return
    
    # 检查MinerU命令是否存在
    if not os.path.exists(MINERU_CMD):
        logger.error(f"MinerU命令不存在: {MINERU_CMD}")
        return
    
    # 创建日志目录
    Path("/home/axlhuang/kb_create/logs").mkdir(parents=True, exist_ok=True)
    
    # 开始处理
    process_pdfs_batch(args.input, args.output, args.workers)

if __name__ == "__main__":
    main()