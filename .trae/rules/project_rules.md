# 项目规则与概览（Trae 用）

## 项目目标
- 将 PDF/Markdown 文档解析成结构化 JSON，并导入数据库，支持批处理与质量校验。

## 运行环境与前置条件
- 开发环境：WSL2（Linux 指令）
- 依赖：`requirements.txt`（Python 版本与包由此约束）

## 目录结构与关键模块
- `src/core/`
  - `config.py`：配置读取与管理
  - `pdf_processor.py`：PDF 解析、OCR 与文本提取
  - `pipeline.py`：处理流水线编排
  - `database.py`：数据库连接与写入
  - `data_importer.py`：将 JSON 导入数据库
- `src/utils/helpers.py`：通用工具函数
- `scripts/`：运维/批处理脚本，如 `process_first_n_pdfs.py`、`run_batch_10_pdfs.py`
- `tests/unit/`：单元与集成测试
- `config/`：环境变量文件（`config.env`、`config.env.example`）
- `input/` 与 `data/input/`：原始/待处理文档

## 常用命令与工作流
- 单次运行：`python main.py`
- 批处理：
  - `python scripts/process_first_n_pdfs.py`
  - `bash simple_batch_process.sh`
- 数据导入与检查：
  - `python scripts/import_json_to_db.py`
  - `python scripts/inspect_db_schema.py`
  - `python scripts/db_quality_check.py`

## 约束与默认规则
- 使用 Linux 指令（WSL2），不提供非 Linux 命令
- 不新增与现有测试文件功能重复的测试
- 尽量不改动非相关模块；修复优先定位根因
- 不新增版权/许可证头，除非明确要求

## 配置与敏感信息
- `.env`/`config.env` 由 `config.env.example` 提示变量；敏感值不入库
- 数据库连接参数只从配置读取，不写死在代码

## 质量与验证
- 先跑变更相关的最小单测，再扩展到综合测试：
  - 例如：`tests/unit/test_pdf_processor_basic.py` → `tests/unit/test_pdf_processor.py`
- 若无现成测试，遵循已有测试模式，新增在相应 `tests/unit/` 路径（避免重复功能）

## 常见问题
- OCR 内存占用：参考 `docs/memory_requirements_analysis.md`
- 规则/约束更新：在此文件维护，并同步到 `README.md` 的“开发须知”

## 开放事项（按需维护）
- TODO：列出当前迭代的待办与限制
