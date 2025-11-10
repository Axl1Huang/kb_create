import os
import json
import argparse
import requests
from typing import Any, Dict, List, Optional

DEFAULT_INPUT_FILE = "/root/kb_create/input/--Radiolysis-of-aqueous-2-chloroanisole_2006_Radiation-Physics-and-Chemistry.md"
DEFAULT_MODEL = os.environ.get("MODEL", "qwen3:30b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OUTPUT_DIR = os.environ.get("KB_OUTPUT_DIR", "/root/kb_create/data/output")
DEFAULT_NUM_CTX = int(os.environ.get("NUM_CTX", "16384"))

SCHEMA_TEMPLATE = {
    "title": None,
    "authors": [],
    "abstract": None,
    "keywords": [],
    "year": None,
    "venue": None,
    "research_field": None,
    "doi": None,
    "references": [],
    "pdf_path": None,
    "pollutants": [],
    "hrt_conditions": None,
    "cod_removal_efficiency": None,
    "enzyme_activities": None
}

def truncate_text(text, max_chars):
    # max_chars <= 0 时不截断，使用全文
    if max_chars is None or max_chars <= 0:
        return text
    return text[:max_chars]

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def infer_metadata_from_filename(file_path: str):
    base = os.path.basename(file_path)
    name = os.path.splitext(base)[0]
    parts = name.split("_")
    year = None
    venue = None
    # 约定: file 格式为 <title>_<year>_<venue>
    for p in parts:
        if p.isdigit() and 1900 <= int(p) <= 2100:
            year = int(p)
    if len(parts) >= 3:
        venue_raw = parts[-1]
        venue = venue_raw.replace("-", " ").strip()
    return year, venue

def normalize_text(text: str) -> str:
    import re
    # 去除 LaTeX 数学块
    text = re.sub(r"\$[^$]*\$", "", text)
    # 去除常见 LaTeX 命令
    text = re.sub(r"\\mathrm\s*\{[^}]*\}", "", text)
    text = re.sub(r"\\mathbf\s*\{[^}]*\}", "", text)
    text = re.sub(r"\\left|\\right|\\cdot|\\times|\\approx|\\to", "", text)
    # 去除 ^{...} 或 _{...}
    text = re.sub(r"\^\s*\{[^}]*\}", "", text)
    text = re.sub(r"_\s*\{[^}]*\}", "", text)
    # 去除控制字符
    text = re.sub(r"[\x00-\x1F]", " ", text)
    # 多空格合并
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_title_from_md(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('#'):
            # remove leading #'s and spaces
            return s.lstrip('#').strip()
    return None

def sanitize_authors(authors):
    if not isinstance(authors, list):
        return authors
    cleaned = []
    for a in authors:
        s = (a or "")
        s = ''.join(ch for ch in s if ord(ch) >= 32)
        s = s.strip()
        if s and s not in cleaned:
            cleaned.append(s)
    return cleaned

def coerce_to_list_of_str(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if isinstance(value, list):
        out: List[str] = []
        for x in value:
            s = str(x or "").strip()
            if s and s not in out:
                out.append(s)
        return out
    return []

def coerce_to_str_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None

def coerce_year(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        s = str(value).strip()
        if s.isdigit():
            y = int(s)
            return y if 1500 <= y <= 2100 else None
        return None
    except Exception:
        return None

def validate_and_fix_schema(data: Dict[str, Any], input_file: str) -> Dict[str, Any]:
    fixed: Dict[str, Any] = {}
    # 初始化基础键
    for k, default in SCHEMA_TEMPLATE.items():
        fixed[k] = data.get(k, default)

    # 类型校正
    fixed["title"] = coerce_to_str_or_none(fixed.get("title"))
    fixed["abstract"] = coerce_to_str_or_none(fixed.get("abstract"))
    fixed["venue"] = coerce_to_str_or_none(fixed.get("venue"))
    fixed["research_field"] = coerce_to_str_or_none(fixed.get("research_field"))
    fixed["doi"] = coerce_to_str_or_none(fixed.get("doi"))
    fixed["pdf_path"] = coerce_to_str_or_none(fixed.get("pdf_path"))
    fixed["year"] = coerce_year(fixed.get("year"))
    fixed["authors"] = sanitize_authors(coerce_to_list_of_str(fixed.get("authors")))
    fixed["keywords"] = coerce_to_list_of_str(fixed.get("keywords"))
    fixed["references"] = coerce_to_list_of_str(fixed.get("references"))
    fixed["pollutants"] = [s.lower() for s in coerce_to_list_of_str(fixed.get("pollutants"))]

    # 摘要清理（通用，不做内容臆造）
    if fixed.get("abstract"):
        fixed["abstract"] = normalize_text(fixed["abstract"])

    # 标题回退：从Markdown首行
    if not fixed.get("title"):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                md_text = f.read()
            md_title = extract_title_from_md(md_text)
            if md_title:
                fixed["title"] = md_title
        except Exception:
            pass

    # 不进行任何基于文件名或路径的回填；仅做格式校验
    # 强制 pdf_path 格式校验：如存在则必须以 .pdf 结尾，否则置为 null
    if fixed.get("pdf_path") and not str(fixed["pdf_path"]).lower().endswith(".pdf"):
        fixed["pdf_path"] = None

    # 其他可空键保证存在
    for k in ["hrt_conditions", "cod_removal_efficiency", "enzyme_activities"]:
        if k not in fixed:
            fixed[k] = None

    # 本次测试不修改关键词与研究领域关系，保持模型原始输出（不做安全清空）

    return fixed

def build_messages(markdown_text, input_file):
    instruction = (
        "请从以下论文全文中抽取核心元数据并以纯 JSON 输出。"
        "严格使用模板中的键，禁止输出任何未在模板出现的键；只返回 JSON，不要额外文字。"
        "缺失字段一律填 null 或空数组，不允许根据标题、文件名、上下文或常识进行推断与回填。"
        "authors、keywords、references、pollutants 必须是字符串数组；year 如无法明确则为 null，否则为整数；doi 无法确定时为 null。"
        "【严格按数据库SQL约束提取】publication_year 仅当正文明确出现出版信息（如 Published/Publication date/Issue/Volume 等可确定出版年的表述）时填写；“Received/Accepted”等日期不得作为出版年；无法确定则 year=null。"
        "venue 仅当正文明确出现期刊或会议名时填写；否则为 null。注意：期刊名如“Radiation Physics and Chemistry”是 venue，不是研究领域。"
        "research_field（研究领域）提取规则：仅当正文出现明确的学科标识或字段（例如 “Subject area: Radiation Chemistry”、“研究领域：辐射化学”、“Field: Environmental Chemistry”等）时填写；不得从标题、keywords、作者信息、期刊名或文件名推断；若无法明确则 research_field=null。为避免后续入库约束冲突，当 research_field 为 null 时 keywords 必须为空数组。"
        "keywords 仅从正文中明确的“Keywords:”或同等段落提取；若正文未明确列出，则输出空数组。不得从标题或常识生成关键词。"
        "references 仅当正文存在明确的参考文献列表时填写；否则为空数组。"
        "doi 仅在正文明确给出（例如以“10.”开头的 DOI）时填写；否则为 null。"
        "pdf_path 仅当正文出现明确的 PDF 链接时填写，且必须以 .pdf 结尾；否则为 null。"
        "pollutants 必须小写；如正文未明确指出污染物名称则输出空数组。"
        "hrt_conditions、cod_removal_efficiency、enzyme_activities 仅当正文明确描述时填写；否则为 null。"
        "不要臆造超出文本明确说明的事实；摘要需移除 LaTeX 与特殊符号并输出为干净文本。"
    )
    template = json.dumps(SCHEMA_TEMPLATE, ensure_ascii=False)
    md_title = extract_title_from_md(markdown_text)
    hints = {
        "file_name": os.path.basename(input_file),
        "md_title": md_title
    }
    content = f"{instruction}\n模板:\n{template}\n提示:\n{json.dumps(hints, ensure_ascii=False)}\n正文:\n{markdown_text}\n"
    return [{"role": "system", "content": "你是结构化信息抽取助手。只输出有效 JSON。摘要需清理LaTeX符号。"},
            {"role": "user", "content": content}]

def call_ollama_chat(url, model, messages, temperature, max_tokens, timeout, num_ctx):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "format": "json",
        "options": {"num_ctx": num_ctx}
    }
    return requests.post(f"{url}/api/chat", json=payload, timeout=timeout)

def parse_json_content(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                return None
        return None

def compute_diff(model_data: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    diffs: Dict[str, Any] = {}
    keys = sorted(set(list(model_data.keys()) + list(baseline.keys())))
    for k in keys:
        mv = model_data.get(k)
        bv = baseline.get(k)
        if mv != bv:
            diffs[k] = {"model": mv, "baseline": bv}
    return diffs

def build_quality_report(data: Dict[str, Any]) -> Dict[str, Any]:
    missing = [k for k, v in SCHEMA_TEMPLATE.items() if (data.get(k) in (None, [], ""))]
    type_issues: List[str] = []
    # 简单类型检查
    if data.get("year") is not None and not isinstance(data.get("year"), int):
        type_issues.append("year:not_int")
    for k in ["authors", "keywords", "references", "pollutants"]:
        if data.get(k) is not None and not isinstance(data.get(k), list):
            type_issues.append(f"{k}:not_list")
    summary = {
        "total_fields": len(SCHEMA_TEMPLATE.keys()),
        "missing_count": len(missing),
        "type_issue_count": len(type_issues)
    }
    return {"summary": summary, "missing_fields": missing, "type_issues": type_issues}

def test_local_model_with_real_paper(input_file=DEFAULT_INPUT_FILE, model=DEFAULT_MODEL,
                                     ollama_url=DEFAULT_OLLAMA_URL, output_dir=DEFAULT_OUTPUT_DIR,
                                     max_chars=5000, temperature=0.0, max_tokens=1600, timeout=300,
                                     num_ctx=DEFAULT_NUM_CTX, baseline_json: Optional[str] = None,
                                     emit_report: bool = True):
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            markdown_text = f.read()
        print(f"读取文件成功: {input_file}  长度: {len(markdown_text)}")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None

    markdown_text = truncate_text(markdown_text, max_chars)
    print(f"使用文本长度: {len(markdown_text)}")

    messages = build_messages(markdown_text, input_file)
    print("调用本地模型")
    try:
        response = call_ollama_chat(ollama_url, model, messages, temperature, max_tokens, timeout, num_ctx)
    except Exception as e:
        print(f"本地模型请求失败: {e}")
        return None

    if response.status_code != 200:
        print(f"调用失败，状态码: {response.status_code}")
        print(response.text)
        return None

    result = response.json()
    content = result.get("message", {}).get("content", "")
    parsed = parse_json_content(content)

    # 后处理: 通用校验与类型纠错，不做内容臆造
    if parsed is not None:
        parsed = validate_and_fix_schema(parsed, input_file)

    ensure_dir(output_dir)
    if parsed is not None:
        out_path = os.path.join(output_dir, "real_paper_test_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"JSON解析成功，已保存: {out_path}")

        # 可选：生成质量报告
        if emit_report:
            quality = build_quality_report(parsed)
            q_path = os.path.join(output_dir, "real_paper_test_quality.json")
            with open(q_path, "w", encoding="utf-8") as f:
                json.dump(quality, f, ensure_ascii=False, indent=2)
            print(f"质量报告已保存: {q_path}")

        # 可选：与基准JSON对比并生成diff
        if emit_report and baseline_json and os.path.exists(baseline_json):
            try:
                with open(baseline_json, "r", encoding="utf-8") as bf:
                    baseline = json.load(bf)
                diffs = compute_diff(parsed, baseline)
                d_path = os.path.join(output_dir, "real_paper_test_diff.json")
                with open(d_path, "w", encoding="utf-8") as f:
                    json.dump(diffs, f, ensure_ascii=False, indent=2)
                print(f"Diff报告已保存: {d_path}")
            except Exception as e:
                print(f"生成Diff报告失败: {e}")
    else:
        raw_path = os.path.join(output_dir, "real_paper_test_raw.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"JSON解析失败，原始输出已保存: {raw_path}")

    return content

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-chars", type=int, default=5000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX)
    parser.add_argument("--baseline-json", type=str, default=None, help="可选的基准JSON用于对比")
    parser.add_argument("--emit-report", action="store_true", help="生成质量与diff报告")
    args = parser.parse_args()
    test_local_model_with_real_paper(
        input_file=args.file,
        model=args.model,
        ollama_url=args.ollama_url,
        output_dir=args.output_dir,
        max_chars=args.max_chars,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
        num_ctx=args.num_ctx,
        baseline_json=args.baseline_json,
        emit_report=args.emit_report
    )