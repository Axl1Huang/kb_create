#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from core.config import Config, setup_logging
from core.pipeline import KnowledgePipeline


def pick_first_n_pdfs(input_dir: Path, n: int = 10):
    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")
    pdfs = list(input_dir.rglob("*.pdf"))
    return pdfs[:n]


def main():
    config = Config()
    config.setup_directories()
    log_file = config.paths.logs_dir / 'batch_10_pdfs.log'
    setup_logging(log_file)

    pipeline = KnowledgePipeline(config)
    input_dir = config.paths.input_dir
    output_md_dir = config.paths.output_dir / 'markdown'

    # 仅处理前10个PDF
    pdfs = pick_first_n_pdfs(input_dir, 10)
    if not pdfs:
        print("未找到PDF文件")
        return

    print(f"将处理前 {len(pdfs)} 个PDF...")

    # 手动批处理这些PDF并将MD放到统一目录
    output_md_dir.mkdir(parents=True, exist_ok=True)
    from core.pdf_processor import PDFProcessor
    processor = PDFProcessor(config)

    results = {"processed": 0, "failed": 0, "errors": []}
    for pdf in pdfs:
        ok = processor.process_single_pdf(pdf, output_md_dir)
        if ok:
            results["processed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(str(pdf))

    print(f"PDF处理完成: 成功 {results['processed']}, 失败 {results['failed']}")

    # 运行导入阶段
    try:
        import_results = pipeline.run_data_import(output_md_dir)
        print(f"数据导入: 成功 {import_results['imported']}, 失败 {import_results['failed']}")
        if import_results.get('errors'):
            print("导入失败文件:")
            for e in import_results['errors']:
                print(f" - {e}")
    except Exception as e:
        print(f"导入阶段发生错误: {e}")


if __name__ == '__main__':
    main()