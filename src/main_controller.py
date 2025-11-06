#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主控协调脚本
协调整个知识图谱构建流程
"""

import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append('/home/axlhuang/kb_create')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/axlhuang/kb_create/logs/main_controller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, config: dict = None):
        """初始化构建器"""
        self.config = config or {
            'pdf_input_dir': '/mnt/e/大模型文献2025年3月/英文文献',
            'md_output_dir': '/home/axlhuang/kb_create/output/md_files',
            'json_output_path': '/home/axlhuang/kb_create/output/parsed_data.json',
            'log_dir': '/home/axlhuang/kb_create/logs'
        }
        
        # 确保目录存在
        Path(self.config['md_output_dir']).mkdir(parents=True, exist_ok=True)
        Path(self.config['log_dir']).mkdir(parents=True, exist_ok=True)
    
    def run_pdf_processing(self) -> bool:
        """
        运行PDF处理阶段
        
        Returns:
            处理是否成功
        """
        logger.info("开始PDF处理阶段")
        
        try:
            cmd = [
                'python3', '/home/axlhuang/kb_create/pdf_processor/pdf_batch_processor.py',
                '-i', self.config['pdf_input_dir'],
                '-o', self.config['md_output_dir']
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1小时超时
            
            if result.returncode == 0:
                logger.info("PDF处理阶段完成")
                return True
            else:
                logger.error(f"PDF处理阶段失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("PDF处理阶段超时")
            return False
        except Exception as e:
            logger.error(f"PDF处理阶段出错: {str(e)}")
            return False
    
    def run_md_parsing(self) -> bool:
        """
        运行MD解析阶段
        
        Returns:
            解析是否成功
        """
        logger.info("开始MD解析阶段")
        
        try:
            cmd = [
                'python3', '/home/axlhuang/kb_create/md_parser/md_parser.py',
                '-i', self.config['md_output_dir'],
                '-o', self.config['json_output_path']
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30分钟超时
            
            if result.returncode == 0:
                logger.info("MD解析阶段完成")
                return True
            else:
                logger.error(f"MD解析阶段失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("MD解析阶段超时")
            return False
        except Exception as e:
            logger.error(f"MD解析阶段出错: {str(e)}")
            return False
    
    def run_data_import(self) -> bool:
        """
        运行数据导入阶段
        
        Returns:
            导入是否成功
        """
        logger.info("开始数据导入阶段")
        
        try:
            cmd = [
                'python3', '/home/axlhuang/kb_create/database_connector/data_importer.py',
                '-i', self.config['json_output_path']
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30分钟超时
            
            if result.returncode == 0:
                logger.info("数据导入阶段完成")
                return True
            else:
                logger.error(f"数据导入阶段失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("数据导入阶段超时")
            return False
        except Exception as e:
            logger.error(f"数据导入阶段出错: {str(e)}")
            return False
    
    def build_knowledge_graph(self, skip_pdf: bool = False, skip_parse: bool = False, skip_import: bool = False) -> bool:
        """
        构建知识图谱
        
        Args:
            skip_pdf: 是否跳过PDF处理阶段
            skip_parse: 是否跳过MD解析阶段
            skip_import: 是否跳过数据导入阶段
            
        Returns:
            构建是否成功
        """
        logger.info("开始构建知识图谱")
        start_time = datetime.now()
        
        # 1. PDF处理阶段
        if not skip_pdf:
            if not self.run_pdf_processing():
                logger.error("PDF处理阶段失败，终止流程")
                return False
        
        # 2. MD解析阶段
        if not skip_parse:
            if not self.run_md_parsing():
                logger.error("MD解析阶段失败，终止流程")
                return False
        
        # 3. 数据导入阶段
        if not skip_import:
            if not self.run_data_import():
                logger.error("数据导入阶段失败，终止流程")
                return False
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"知识图谱构建完成，耗时: {duration}")
        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="知识图谱构建主控脚本")
    parser.add_argument("--skip-pdf", action="store_true", help="跳过PDF处理阶段")
    parser.add_argument("--skip-parse", action="store_true", help="跳过MD解析阶段")
    parser.add_argument("--skip-import", action="store_true", help="跳过数据导入阶段")
    parser.add_argument("--pdf-only", action="store_true", help="仅运行PDF处理阶段")
    parser.add_argument("--parse-only", action="store_true", help="仅运行MD解析阶段")
    parser.add_argument("--import-only", action="store_true", help="仅运行数据导入阶段")
    
    args = parser.parse_args()
    
    # 创建构建器实例
    builder = KnowledgeGraphBuilder()
    
    # 根据参数决定运行模式
    if args.pdf_only:
        success = builder.run_pdf_processing()
    elif args.parse_only:
        success = builder.run_md_parsing()
    elif args.import_only:
        success = builder.run_data_import()
    else:
        # 完整流程
        skip_pdf = args.skip_pdf
        skip_parse = args.skip_parse
        skip_import = args.skip_import
        success = builder.build_knowledge_graph(skip_pdf, skip_parse, skip_import)
    
    if success:
        logger.info("知识图谱构建成功完成")
        sys.exit(0)
    else:
        logger.error("知识图谱构建失败")
        sys.exit(1)

if __name__ == "__main__":
    main()