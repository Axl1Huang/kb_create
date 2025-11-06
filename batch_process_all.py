#!/usr/bin/env python3
"""
批量处理所有英文文献的脚本
遍历所有分组内的PDF文件并进行处理
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
import time

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 基础目录
BASE_DIR = "/mnt/e/大模型文献2025年3月/英文文献"
INPUT_DIR = "/home/axlhuang/kb_create/test_input"
OUTPUT_BASE_DIR = "/home/axlhuang/kb_create/batch_output"
PROCESSED_LOG = "/home/axlhuang/kb_create/batch_processed.log"

def get_all_pdf_groups():
    """获取所有PDF分组目录"""
    groups = []
    for root, dirs, files in os.walk(BASE_DIR):
        # 查找包含PDF文件的目录
        pdf_files = [f for f in files if f.endswith('.pdf')]
        if pdf_files:
            groups.append(root)
            logger.info(f"找到分组目录: {root} (包含 {len(pdf_files)} 个PDF文件)")
    return groups

def copy_pdfs_to_input_dir(group_dir, max_files=10):
    """复制指定数量的PDF文件到输入目录"""
    # 清空输入目录
    if os.path.exists(INPUT_DIR):
        for file in os.listdir(INPUT_DIR):
            os.remove(os.path.join(INPUT_DIR, file))
    else:
        os.makedirs(INPUT_DIR, exist_ok=True)
    
    # 复制PDF文件
    pdf_files = [f for f in os.listdir(group_dir) if f.endswith('.pdf')]
    copied_files = []
    
    for i, pdf_file in enumerate(pdf_files[:max_files]):
        src_path = os.path.join(group_dir, pdf_file)
        dst_path = os.path.join(INPUT_DIR, pdf_file)
        
        try:
            # 复制文件
            with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                dst.write(src.read())
            copied_files.append(pdf_file)
            logger.info(f"已复制文件 {i+1}/{min(max_files, len(pdf_files))}: {pdf_file}")
        except Exception as e:
            logger.error(f"复制文件失败 {pdf_file}: {e}")
    
    return copied_files

def run_processing_pipeline():
    """运行处理管道"""
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['DASHSCOPE_API_KEY'] = 'sk-2f1e5c15eed5463a9f05c2f8d6d49f8a'
        
        # 运行主程序
        cmd = [
            sys.executable, 
            'main.py', 
            '--log-level', 'INFO'
        ]
        
        logger.info("开始运行处理管道...")
        result = subprocess.run(
            cmd, 
            cwd='/home/axlhuang/kb_create',
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )
        
        if result.returncode == 0:
            logger.info("处理管道运行成功")
            logger.debug(f"标准输出: {result.stdout}")
            return True
        else:
            logger.error(f"处理管道运行失败，返回码: {result.returncode}")
            logger.error(f"错误输出: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("处理管道运行超时")
        return False
    except Exception as e:
        logger.error(f"运行处理管道时发生异常: {e}")
        return False

def move_processed_files(processed_files, group_name):
    """移动处理完成的文件到对应的输出目录"""
    output_dir = os.path.join(OUTPUT_BASE_DIR, group_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 移动Markdown文件
    markdown_dir = "/home/axlhuang/kb_create/output/markdown"
    if os.path.exists(markdown_dir):
        for file in os.listdir(markdown_dir):
            if file.endswith('.md'):
                src_path = os.path.join(markdown_dir, file)
                dst_path = os.path.join(output_dir, file)
                try:
                    os.rename(src_path, dst_path)
                    logger.info(f"已移动文件: {file} -> {output_dir}")
                except Exception as e:
                    logger.error(f"移动文件失败 {file}: {e}")

def log_processed_group(group_dir):
    """记录已处理的分组"""
    with open(PROCESSED_LOG, 'a') as f:
        f.write(f"{group_dir}\n")

def is_group_processed(group_dir):
    """检查分组是否已处理"""
    if not os.path.exists(PROCESSED_LOG):
        return False
    
    with open(PROCESSED_LOG, 'r') as f:
        processed_groups = f.read().splitlines()
    
    return group_dir in processed_groups

def main():
    """主函数"""
    logger.info("开始批量处理所有英文文献...")
    
    # 获取所有分组
    groups = get_all_pdf_groups()
    logger.info(f"总共找到 {len(groups)} 个分组目录")
    
    success_count = 0
    failed_count = 0
    
    # 处理每个分组
    for i, group_dir in enumerate(groups):
        logger.info(f"处理分组 {i+1}/{len(groups)}: {group_dir}")
        
        # 检查是否已处理
        if is_group_processed(group_dir):
            logger.info(f"跳过分组 {group_dir} (已处理)")
            continue
        
        try:
            # 复制PDF文件到输入目录
            copied_files = copy_pdfs_to_input_dir(group_dir, max_files=10)
            if not copied_files:
                logger.warning(f"分组 {group_dir} 中没有找到PDF文件")
                continue
            
            logger.info(f"开始处理 {len(copied_files)} 个PDF文件")
            
            # 运行处理管道
            success = run_processing_pipeline()
            
            if success:
                # 移动处理完成的文件
                group_name = os.path.basename(group_dir)
                move_processed_files(copied_files, group_name)
                
                # 记录已处理的分组
                log_processed_group(group_dir)
                
                success_count += 1
                logger.info(f"分组 {group_dir} 处理成功")
            else:
                failed_count += 1
                logger.error(f"分组 {group_dir} 处理失败")
            
            # 等待一段时间再处理下一个分组
            time.sleep(30)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"处理分组 {group_dir} 时发生异常: {e}")
    
    logger.info(f"批量处理完成! 成功: {success_count}, 失败: {failed_count}")

if __name__ == "__main__":
    main()