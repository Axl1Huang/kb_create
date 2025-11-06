#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from md_parser import MDParser
from db_manager import DatabaseManager
from data_inserter import DataInserter

def main():
    """
    主函数，执行完整的数据处理流程
    """
    print("开始执行完整的数据处理流程...")
    
    # 加载配置文件
    load_dotenv("/home/axlhuang/kb_create/config.env")
    
    # 获取配置的目录
    output_dir = Path(os.getenv("OUTPUT_DIR", "/home/axlhuang/kb_create/output"))
    logs_dir = Path(os.getenv("LOGS_DIR", "/home/axlhuang/kb_create/logs"))
    
    # 1. 创建数据插入器实例
    inserter = DataInserter()
    
    # 2. 连接数据库
    print("正在连接数据库...")
    if not inserter.connect_database():
        print("数据库连接失败，流程终止")
        return
    
    try:
        # 3. 解析MD文件并插入数据
        print("正在解析MD文件并插入数据...")
        md_directory = output_dir
        
        if not md_directory.exists():
            print(f"MD文件目录不存在: {md_directory}")
            return
        
        # 遍历所有分组目录
        group_dirs = [d for d in md_directory.iterdir() if d.is_dir()]
        
        for group_dir in group_dirs:
            print(f"正在处理分组: {group_dir.name}")
            
            # 解析该目录下的所有MD文件
            papers = inserter.parser.parse_directory(group_dir)
            
            print(f"  找到 {len(papers)} 篇文献")
            
            # 插入每篇文献的数据
            for paper_info in papers:
                inserter.insert_paper_data(paper_info)
        
        print("所有数据处理完成")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        # 记录错误日志
        log_file = logs_dir / "error.log"
        with open(log_file, "a") as f:
            f.write(f"Error: {e}\n")
    finally:
        # 4. 断开数据库连接
        inserter.disconnect_database()
        print("数据库连接已关闭")

if __name__ == "__main__":
    main()