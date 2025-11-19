# 项目概览

- 三阶段并行处理：PDF→Markdown→JSON→数据库，使用队列衔接，持续推进而非整批等待
- GPU分工：`GPU0` 执行 PDF→MD（MinerU）；`GPU1` 执行 MD→JSON（本地模型解析服务），数据库入库并行批量写入
- 质量基线：标题解析稳定、参考文献抽取覆盖率高；摘要在多数 MD 中缺失或未提供；作者与年份在当前语料中普遍缺失
- 去重策略：优先按 `doi` 更新；无 `doi` 时按 `title` 幂等插入（存在同名不同文献的风险）

# 目录结构与日志

- Markdown输出：`data/output/markdown/*.md`
- MinerU日志：`logs/mineru/*.out.log`、`*.err.log`
- 阶段进度：`logs/pdf_progress.jsonl`
- 并行性能：`logs/dual_gpu_performance.jsonl`
- 并行运行：`logs/parallel_run*.log`、`logs/md_import_accel_*.log`

# 运行方式

## PDF→MD（GPU0）

- 环境示例：
  - `INPUT_DIR="/root/Downloads/小于等于15MB"`
  - `MINERU_DEVICE=cuda:0`
  - `PDF_MAX_WORKERS=4`
  - `MINERU_FAST_DEFAULT=True`
- 命令示例：
  - `python /root/kb_create/main.py --skip-import --log-level INFO --stats-every 200`

## MD→JSON解析（GPU1）与入库

- 启动本地解析服务（示例）：
  - `CUDA_VISIBLE_DEVICES=1 ollama serve`
  - 服务地址：`OLLAMA_URL=http://127.0.0.1:11434`
- 解析参数（环境变量）：
  - `LLM_DEVICE=cuda:1`
  - `LLM_TIMEOUT=0`（无限超时）
  - `LLM_MAX_TOKENS=0`（不限制）
  - `LLM_MAX_CHARS=0`（不截断）
  - `LLM_NUM_CTX=32768`
- 全量回填入库（示例）：
  - 代码入口：`src/core/data_importer.py:225-253`
  - 批量导入方法：`DataImporter.import_batch(md_files)`

## 并行管线（同时进行三阶段）

- 管线入口：`src/core/dual_gpu_pipeline.py:389-474`
- 队列与线程：`pdf_queue`、`md_queue`、`json_queue`；`num_pdf_workers`、`num_md_workers`、`num_import_workers`
- 设备分配：
  - PDF线程固定 `cuda:0` 或轮询分配
  - 解析线程通过本地模型服务绑定 `cuda:1`

# 关键代码位置

- 批量入库：`src/core/data_importer.py:225-253`
- 单文件入库与解析：`src/core/data_importer.py:27-52`
- 论文入库主流程：`src/core/data_importer.py:64-220`
- PDF处理器：`src/core/pdf_processor.py`
- LLM解析器：`src/core/llm_parser.py`
- 管线与并行：`src/core/dual_gpu_pipeline.py`
- 数据库管理：`src/core/database.py:35-53`（连接池）

# 质量与失败策略

- 标题：来自 MD 首级标题或正文结构，解析成功即入库；当前不做兜底，若缺失则入库失败
- 参考文献：从 `References/参考文献` 章节解析并存储于 `paper_metadata`（键：`references`）
- 摘要：若 MD 未提供 `Abstract/摘要` 章节则可能为空，不影响入库成功
- 失败保留：遵循“不做兜底”的设定，保留失败样本用于后续人工或二次解析

# 去重与一致性

- 有 `doi`：按 `doi` 查重更新（避免重复）；见 `src/core/data_importer.py:98-126`
- 无 `doi`：按 `title` 幂等插入（可能存在同名风险）；见 `src/core/data_importer.py:127-138`
- 关联表批量写入：作者与关键词关联使用 `ON CONFLICT DO NOTHING` 保持幂等；见 `src/core/data_importer.py:156-164, 183-191`

# 监控与诊断

- GPU负载与显存：`nvidia-smi`
- 队列与吞吐：`logs/dual_gpu_performance.jsonl`（包含 `pdf_queue_size`、`md_parsed`、`json_imported`）
- 阶段进度：`logs/pdf_progress.jsonl`
- 入库失败样本列表：批量导入返回 `errors` 字段或日志行

# 常见问题

- `paper.title` 为空触发数据库 NOT NULL：解析器未抽到标题，当前不兜底，保留失败
- 解析性能低或超时：确保解析服务绑定 `GPU1`，并维持无限制参数；适度提高解析与入库并行度
- 重复数据：无 `doi` 的记录按 `title` 幂等，存在同名风险；可后续生成重复风险报告抽样核查