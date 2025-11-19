#!/usr/bin/env bash
set -euo pipefail

# 说明：
# - 每 5 分钟增量解析最近产生的 Markdown，并导入对应 JSON 到数据库。
# - 依赖现有脚本：llm_parse_md_to_json.py 与 import_json_to_db.py。
# - 设计为幂等：重复解析/导入不会破坏数据（导入阶段已做去重与冲突规避）。

MD_DIR="/root/kb_create/data/output/markdown"
JSON_DIR="/root/kb_create/data/output/json_full_parser"
INTERVAL_MIN=5

echo "[sync-ingest] MD_DIR=${MD_DIR} JSON_DIR=${JSON_DIR} interval=${INTERVAL_MIN}min"

while true; do
  TS="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[${TS}] 解析最近 ${INTERVAL_MIN} 分钟的 Markdown..."

  # 解析最近生成/修改的 MD（以文件修改时间判断）
  # - 使用 xargs -r 避免空输入时报错
  # - 单文件模式调用解析脚本，避免全量重复解析
  find "${MD_DIR}" -maxdepth 1 -type f -name '*.md' -mmin -${INTERVAL_MIN} -print0 \
    | xargs -0 -r -I{} python3 /root/kb_create/scripts/llm_parse_md_to_json.py --md "{}" --out-dir "${JSON_DIR}" || true

  echo "[${TS}] 导入最近 ${INTERVAL_MIN}*2 分钟内的 JSON..."
  # 导入最近生成/修改的 JSON（时间窗口稍大，覆盖解析延迟）
  find "${JSON_DIR}" -maxdepth 1 -type f -name '*.json' -mmin -$((INTERVAL_MIN*2)) -print0 \
    | xargs -0 -r -I{} python3 /root/kb_create/scripts/import_json_to_db.py --json "{}" || true

  echo "[${TS}] 休眠 ${INTERVAL_MIN} 分钟..."
  sleep $((INTERVAL_MIN*60))
done