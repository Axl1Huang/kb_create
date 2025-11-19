#!/usr/bin/env python3
"""
设置输入目录并开始处理文献
"""
import sys
import os
from pathlib import Path
import shutil

def setup_input_directory():
    """设置输入目录"""
    # 源目录
    source_dir = Path("/root/Downloads/小于等于15MB")
    # 目标输入目录
    target_dir = Path("/root/kb_create/data/input")

    # 创建目标目录
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"源目录: {source_dir}")
    print(f"目标目录: {target_dir}")

    # 检查源目录是否存在
    if not source_dir.exists():
        print(f"源目录 {source_dir} 不存在")
        return False

    # 获取源目录中的PDF文件
    pdf_files = list(source_dir.glob("*.pdf"))
    print(f"找到 {len(pdf_files)} 个PDF文件")

    if len(pdf_files) == 0:
        print("源目录中没有PDF文件")
        return False

    # 复制前10个文件作为测试
    test_files = pdf_files[:10]
    print(f"复制前 {len(test_files)} 个文件作为测试...")

    for pdf_file in test_files:
        target_file = target_dir / pdf_file.name
        if not target_file.exists():
            shutil.copy2(pdf_file, target_file)
            print(f"已复制: {pdf_file.name}")
        else:
            print(f"已存在，跳过: {pdf_file.name}")

    print(f"已完成复制 {len(test_files)} 个文件到 {target_dir}")
    return True

def run_processing():
    """运行处理"""
    print("开始运行处理...")

    # 导入必要的模块
    sys.path.insert(0, str(Path(__file__).parent / 'src'))

    # 直接从core.config导入UnifiedConfig
    from src.core.config import UnifiedConfig
    from src.config.logging_config import setup_logging
    from src.core.pipeline import KnowledgePipeline

    # 加载配置
    config = UnifiedConfig()
    config.setup_directories()

    # 设置日志
    log_file = config.paths.logs_dir / "processing.log"
    logger = setup_logging(log_file, "INFO")

    # 创建管道
    pipeline = KnowledgePipeline(config)

    # 运行管道（限制处理10个PDF文件）
    results = pipeline.run_full_pipeline(
        limit_pdfs=10,
        stats_every=2
    )

    # 输出结果
    print("\n" + "=" * 50)
    print("执行结果:")
    print("=" * 50)

    if results['success']:
        print("✅ 管道执行成功")
    else:
        print("❌ 管道执行失败")

    if results.get('pdf_processing'):
        pdf = results['pdf_processing']
        print(f"📄 PDF处理: {pdf['processed']} 成功, {pdf['failed']} 失败")

    if results.get('data_import'):
        imp = results['data_import']
        print(f"💾 数据导入: {imp['imported']} 成功, {imp['failed']} 失败")

    if results.get('error'):
        print(f"❗ 错误: {results['error']}")

    print("=" * 50)
    return results['success']

def main():
    print("设置输入目录并处理文献")
    print("=" * 50)

    # 设置输入目录
    if not setup_input_directory():
        return 1

    # 运行处理
    success = run_processing()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())