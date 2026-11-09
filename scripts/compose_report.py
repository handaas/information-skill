#!/usr/bin/env python3
"""Compose an information big-data report by orchestrating the information MCP.

Calls the upstream information-mcp-server tools and assembles a structured JSON
payload rendered into a professional HTML / Markdown report. Supports
``--dry-run`` which returns a well-formed skeleton from the bundled sample data
WITHOUT contacting the MCP.

The information MCP uses newer-style tools with Literal ``view`` selectors and
type hints; there is no separate fuzzy search. Tools split into two semantics:
  * Enterprise tools (``information_company_news`` / ``information_monitor``):
    treat ``matchKeyword`` as an enterprise identifier with ``keywordType``.
  * Keyword/topic tools (``information_search`` / ``information_industry_news``
    / ``information_topic``): treat ``matchKeyword`` as a topic/industry keyword.

This file never prints secrets; MCP credentials live in the server's own .env.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import pathlib
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from common import REPORT_BANNER, REPORT_TYPE, attach_pagination, call_tool_once, collect_detail_pages, die, json_dumps, load_json_file, paid_call_scope, print_json
import mcp_client
from semantic_review import prepare_draft
from render_report import render_html, render_markdown, html_to_pdf

SAMPLE_PATH = pathlib.Path(__file__).resolve().parent.parent / "assets" / "report.example.json"

# Information MCP tools.
T_SEARCH = "information_search"
T_COMPANY_NEWS = "information_company_news"
T_INDUSTRY_NEWS = "information_industry_news"
T_TOPIC = "information_topic"
T_MONITOR = "information_monitor"

DEFAULT_MONITOR_VIEW = "statistics"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _is_empty_response(value: Any) -> bool:
    if value is None or value == "" or value == {}:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return any(token in text for token in ("查询数据为空", "暂无数据", "未查询到", "未检索到", "no data"))
    if isinstance(value, dict):
        for key in ("text", "message", "msg"):
            if key in value and _is_empty_response(value.get(key)):
                return True
        containers = [value.get(key) for key in ("resultList", "list", "items", "data") if key in value]
        if containers and all(item in (None, [], {}) for item in containers):
            total = value.get("total")
            return total in (None, 0, "0")
    return False


def _is_api_error(value: Any) -> bool:
    """Return True only for failed calls; platform empty-data text is not an error."""
    if value is None or _is_empty_response(value):
        return False
    if isinstance(value, str):
        text = value.lower()
        return any(token in text for token in (
            "接口调用失败", "查询失败", "状态码：4", "状态码：5",
            "upstream timeout", "tool failed", "unauthorized", "forbidden",
        ))
    if isinstance(value, dict):
        if value.get("isError") is True or value.get("is_error") is True or value.get("success") is False:
            return True
        if any(value.get(key) not in (None, "", False) for key in ("_error", "error")):
            return True
        code = value.get("code")
        if code not in (None, 0, "0", 200, "200", 10001, "10001"):
            return True
        return any(_is_api_error(value.get(key)) for key in ("text", "message", "msg") if key in value)
    return False


def _first_list(value: Any) -> List[Any]:
    if _is_api_error(value) or _is_empty_response(value):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("resultList", "list", "items"):
            if isinstance(value.get(key), list):
                return value[key]
        nested = value.get("data")
        if isinstance(nested, list):
            return nested
        if isinstance(nested, dict):
            return _first_list(nested)
    return []


def _first_record(value: Any) -> Dict[str, Any]:
    if _is_api_error(value) or _is_empty_response(value):
        return {}
    for record in _first_list(value):
        if isinstance(record, dict) and _has_evidence(record):
            return record
    if isinstance(value, dict):
        envelope = {"resultList", "list", "items", "data", "total", "pageNo", "pageSize", "text", "message", "msg", "code"}
        if not set(value).issubset(envelope) and _has_evidence(value):
            return value
    return {}


def _has_evidence(value: Any) -> bool:
    if value is None or value == "" or value == "-":
        return False
    if _is_api_error(value) or _is_empty_response(value):
        return False
    if isinstance(value, dict):
        return any(_has_evidence(item) for key, item in value.items() if key not in {"total", "pageNo", "pageSize"})
    if isinstance(value, (list, tuple, set)):
        return any(_has_evidence(item) for item in value)
    return True


def _meaningful_row(row: Mapping[str, Any]) -> bool:
    return any(_has_evidence(value) for value in row.values())


def _attach_call_status(report: Dict[str, Any], calls: Mapping[str, Any]) -> Dict[str, Any]:
    """Disclose failed and genuine-empty domains without exposing upstream details."""
    failed = [name for name, payload in calls.items() if _is_api_error(payload)]
    empty = [name for name, payload in calls.items() if not _is_api_error(payload) and _is_empty_response(payload)]
    source = report.setdefault("data_source", {})
    source["failed_products"] = failed
    source["empty_products"] = empty
    return report


def _apply_resolution_limit(report: Dict[str, Any], resolved: Mapping[str, Any]) -> Dict[str, Any]:
    subject = report.setdefault("subject", {})
    subject["resolved"] = False
    subject["requires_confirmation"] = True
    subject["resolve_reason"] = resolved.get("reason", "主体未唯一确认")
    subject["candidate_sample"] = list(resolved.get("candidate_sample") or [])
    if resolved.get("fuzzy_total") is not None:
        subject["fuzzy_total"] = resolved.get("fuzzy_total")
    message = "输入未唯一确认到特定企业；已停止主体专属数据调用，不生成该企业的经营、风险或舆情评价。请使用候选企业全称或企业标识重试。"
    report["abstract"] = message
    report["summary"] = message
    report["executive_summary"] = [message]
    report["metrics"] = []
    report["representative_records"] = []
    report["insights"] = [{"feature": "主体确认受限", "evidence": subject["resolve_reason"], "interpretation": message}]
    report.setdefault("data_source", {})["subject_resolution"] = "confirmation_required"
    return report


def _text(value: Any, limit: int = 0) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        t = json.dumps(value, ensure_ascii=False)
    else:
        t = str(value)
    t = " ".join(t.split())
    if limit and len(t) > limit:
        return t[: limit - 1].rstrip() + "…"
    return t


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_call(tool: str, arguments: Dict[str, Any]) -> Any:
    try:
        result = call_tool_once(mcp_client.call_tool, tool, arguments)
        # Detect API error responses (405, etc.) and return error marker
        if _is_api_error(result):
            return {"_error": "API错误", "_raw": result}
        return result
    except Exception as exc:
        return {"_error": str(exc)}


def _safe_total(payload: Any) -> Any:
    if isinstance(payload, dict):
        if payload.get("total") is not None:
            return payload.get("total")
        if payload.get("dataTotal") is not None:
            return payload.get("dataTotal")
    return None


def _is_error(payload: Any) -> bool:
    return isinstance(payload, dict) and ("error" in payload or "_error" in payload)


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #

def resolve_enterprise_name(raw: str) -> Dict[str, Any]:
    """Decide whether the raw input is an enterprise name or a topic keyword.

    Information MCP has no fuzzy search. For enterprise tools we still try to
    treat company-like inputs as full names; otherwise we keep the raw keyword.
    """
    raw = (raw or "").strip()
    if not raw:
        return {"keyword": "", "enterprise": "", "resolved": False, "reason": "关键词为空", "subject_type": "topic"}
    if any(suffix in raw for suffix in ("公司", "集团", "有限", "院", "厂", "中心", "事务所", "合作社", "合伙")):
        return {"keyword": raw, "enterprise": raw, "resolved": True, "reason": "视为企业全称", "subject_type": "enterprise"}
    return {"keyword": raw, "enterprise": "", "resolved": True, "reason": "按资讯主题关键词检索", "subject_type": "topic"}


# Legacy sample-scoped metric labels removed from composer output; used only by
# apply_content_review() to clean older payloads.
SAMPLE_METRIC_LABELS = {"资讯来源数", "高频来源", "舆情监控周期", "正面占比"}


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #

def build_subject(raw: str, resolved: Mapping[str, Any], keyword_type: str, opts: Mapping[str, Any]) -> Dict[str, Any]:
    subject_type = resolved.get("subject_type") or "enterprise"
    match_keyword = resolved.get("keyword") or resolved.get("enterprise") or raw
    return {
        "enterprise": (resolved.get("enterprise") or raw) if subject_type == "enterprise" else "",
        "subject_type": subject_type,
        "matchKeyword": match_keyword,
        "keywordType": keyword_type,
        "match_raw": raw,
        "resolved": bool(resolved.get("resolved")),
        "resolve_reason": resolved.get("reason", ""),
        "pub_date_begin": opts.get("pub_start") or "",
        "pub_date_end": opts.get("pub_end") or "",
        "sentiment_label": opts.get("sentiment") or "",
        "monitor_view": opts.get("view") or DEFAULT_MONITOR_VIEW,
    }


def build_metrics(company_total: Any, industry_total: Any, topic_total: Any, stats: Mapping[str, Any]) -> List[Dict[str, Any]]:
    metrics: List[Dict[str, Any]] = []
    if company_total is not None:
        metrics.append({"label": "企业资讯数", "value": _text(company_total), "hint": "企业新闻舆情明细总数"})
    if industry_total is not None:
        metrics.append({"label": "行业资讯数", "value": _text(industry_total), "hint": "行业资讯命中数"})
    if topic_total is not None:
        metrics.append({"label": "主题资讯数", "value": _text(topic_total), "hint": "主题跟踪命中数"})
    s = stats if isinstance(stats, dict) and not _is_error(stats) else {}
    # newsSentimentStats: dict of sentiment->count
    raw_sentiment_stats = s.get("newsSentimentStats")
    sentiment_stats: Mapping[str, Any] = raw_sentiment_stats if isinstance(raw_sentiment_stats, dict) else {}
    label_map = {"positive": "正面", "negative": "负面", "neutral": "中性", "unknown": "未知"}
    # Pre-compute shares for delta annotations.
    total_sent = 0.0
    sent_counts: Dict[str, float] = {}
    for key in ("positive", "negative", "neutral", "unknown"):
        try:
            raw_count = sentiment_stats.get(key)
            if raw_count is None:
                raise ValueError("missing sentiment count")
            n = float(raw_count)
            sent_counts[key] = n
            total_sent += n
        except (TypeError, ValueError):
            sent_counts[key] = 0.0
    for key, label in (("positive", "正面资讯"), ("negative", "负面资讯"), ("neutral", "中性资讯")):
        val = sentiment_stats.get(key)
        if val is not None:
            entry: Dict[str, Any] = {"label": label, "value": _text(val), "hint": f"{label_map.get(key)}情感资讯数"}
            if total_sent > 0:
                entry["delta"] = f"占比 {sent_counts[key] / total_sent * 100:.0f}%"
            metrics.append(entry)
    return [m for m in metrics if m.get("value") not in ("", None, "-")]


def requested_products(subject: Mapping[str, Any]) -> List[Dict[str, str]]:
    products: List[Dict[str, str]] = []
    if subject.get("subject_type") == "enterprise":
        products.extend([
            {"name": "企业资讯查询", "product_id": "66b485eadaf8c77fb249a455"},
            {"name": "企业资讯监控", "product_id": "66b338e274bf098447db7efd"},
        ])
    products.extend([
        {"name": "资讯全文检索", "product_id": "6a60928a935bb6a5c6bbd68f"},
        {"name": "资讯主题跟踪", "product_id": "6a60928a935bb6a5c6bbd68f"},
    ])
    return products


def build_caliber(subject: Mapping[str, Any], opts: Mapping[str, Any]) -> Dict[str, Any]:
    sentiment_hint = ""
    raw_sentiment = opts.get("sentiment")
    if raw_sentiment not in (None, ""):
        try:
            sentiment_name = _SENTIMENT_LABEL_MAP.get(int(raw_sentiment), "未知")
        except (TypeError, ValueError):
            sentiment_name = _text(raw_sentiment)
        sentiment_hint = f"；明细筛选：情感={sentiment_name}"
    date_hint = ""
    if opts.get("pub_start") or opts.get("pub_end"):
        date_hint = f"；发布区间 {opts.get('pub_start') or '不限'}~{opts.get('pub_end') or '不限'}"
    products = [item["name"] for item in requested_products(subject)]
    return {
        "match_target": subject.get("enterprise") or subject.get("match_raw"),
        "match_type": f"企业资讯按企业主体匹配；行业/主题/全文检索按关键词匹配{sentiment_hint}{date_hint}",
        "data_scope": "、".join(products),
        "products": products,
        "limit": "数据来自公开新闻资讯；记录数不等于独立事件数，跨产品数量不可相加。全文检索、主题跟踪及企业资讯可能返回同题转载或相同记录，报告未执行跨产品去重。",
    }


_SENTIMENT_LABEL_MAP = {0: "负面", 1: "正面", 2: "中性", 3: "未知"}


def _sentiment_text(value: Any) -> str:
    """sentimentLabel is an int (0/1/2/3) → map to 正面/负面/中性/未知.
    Falls back gracefully for stringified ints or pre-translated labels."""
    if value is None or value == "":
        return "-"
    # int-like (including "0"/"1"/"2"/"3")
    try:
        iv = int(value)
        return _SENTIMENT_LABEL_MAP.get(iv, _text(value))
    except (TypeError, ValueError):
        return _text(value)


def _news_rows(payload: Any, *, title_key: str = "informationTitle") -> List[Dict[str, Any]]:
    rows = []
    for item in _first_list(payload):
        if not isinstance(item, dict):
            continue
        rows.append({
            "标题": _text(item.get(title_key) or item.get("newsTitle") or item.get("title")) or "-",
            "来源": _text(item.get("informationSource") or item.get("newsSource") or item.get("source")) or "-",
            "发布时间": _text(item.get("informationPublishTime") or item.get("newsPublishTime") or item.get("publishTime")) or "-",
            "情感": _sentiment_text(item.get("sentimentLabel")),
            "链接": _text(item.get("newsLink") or item.get("informationLink") or item.get("link")) or "-",
            "简介": _text(item.get("informationBrief") or item.get("newsBrief") or item.get("brief"), limit=80) or "-",
        })
    return rows


_ENTITY_TYPE_MAP = {
    "enterprise": "企业",
    "company": "企业",
    "person": "个人",
    "organization": "机构",
    "organisation": "机构",
    "institution": "机构",
    "government": "政府",
    "university": "高校",
}


def _self_entity_key(value: Any) -> str:
    """Presentation-only key for subject self-exclusion.

    Only full/half-width bracket variants and whitespace are normalized; other
    punctuation is preserved so distinct legal names are not conflated.
    """
    text = _text(value).strip().lower()
    for src, dst in (("（", "("), ("）", ")"), ("【", "["), ("】", "]")):
        text = text.replace(src, dst)
    return "".join(ch for ch in text if not ch.isspace())


def _entity_type_text(value: Any) -> str:
    text = _text(value)
    return _ENTITY_TYPE_MAP.get(text.lower(), text) if text else "-"


def _related_enterprises_rows(payload: Any, *, exclude_name: str = "") -> List[Dict[str, Any]]:
    """Aggregate co-mentioned enterprises from resultList[].relatedEnterprises.

    Self-exclusion compares presentation-only keys (full/half-width brackets
    and whitespace). Other entities are keyed by their exact raw name; distinct
    names are never merged without identity evidence. Returns at most 15 rows;
    callers must not present len(rows) as the total number of co-mentioned
    entities.
    """
    counter: Dict[str, Dict[str, Any]] = {}
    exclude_key = _self_entity_key(exclude_name)
    for item in _first_list(payload):
        if not isinstance(item, dict):
            continue
        rel = item.get("relatedEnterprises")
        if not isinstance(rel, list):
            continue
        for ent in rel:
            if not isinstance(ent, dict):
                continue
            name = _text(ent.get("name")).strip()
            if not name or (exclude_key and _self_entity_key(name) == exclude_key):
                continue
            entry = counter.setdefault(name, {"企业名称": name, "类型": _entity_type_text(ent.get("entityType")), "共现次数": 0})
            try:
                entry["共现次数"] = int(entry["共现次数"]) + 1
            except (TypeError, ValueError):
                entry["共现次数"] = 1
    rows = list(counter.values())
    rows.sort(key=lambda r: r.get("共现次数", 0), reverse=True)
    return rows[:15]


def build_core_analysis(
    company_news: Any,
    monitor_stats: Any,
    industry_news: Any,
    topic_news: Any,
    opts: Mapping[str, Any],
) -> Dict[str, Any]:
    # 企业资讯明细表
    company_rows = _news_rows(company_news, title_key="informationTitle")
    company_total = company_news.get("total") if isinstance(company_news, dict) else None

    # 企业资讯统计 KV（from monitor statistics view）
    stats_kv: Dict[str, Any] = {}
    s: Mapping[str, Any] = monitor_stats if isinstance(monitor_stats, dict) and not _is_error(monitor_stats) else {}
    raw_sentiment_stats = s.get("newsSentimentStats")
    sentiment_stats: Mapping[str, Any] = raw_sentiment_stats if isinstance(raw_sentiment_stats, dict) else {}
    label_map = {"positive": "正面", "negative": "负面", "neutral": "中性", "unknown": "未知"}
    for key in ("positive", "negative", "neutral", "unknown"):
        val = sentiment_stats.get(key)
        if val is not None:
            stats_kv[label_map[key]] = _text(val)
    if isinstance(s.get("sentimentLabelList"), list) and s["sentimentLabelList"]:
        reverse_map = {"positive": "正面", "negative": "负面", "neutral": "中性", "unknown": "未知"}
        stats_kv["情感类别"] = "、".join(reverse_map.get(str(t).lower(), _text(t)) for t in s["sentimentLabelList"] if t)
    # 趋势
    trend_rows: List[Dict[str, Any]] = []
    news_trend = s.get("newsSentimentTrend")
    if isinstance(news_trend, dict):
        months = news_trend.get("month")
        if isinstance(months, list):
            raw_stats_list = news_trend.get("stats")
            stats_dict: List[Any] = raw_stats_list if isinstance(raw_stats_list, list) else []
            for idx, m in enumerate(months):
                row = {"周期/月份": _text(m)}
                raw_stats_item = stats_dict[idx] if idx < len(stats_dict) else {}
                stats_item: Mapping[str, Any] = raw_stats_item if isinstance(raw_stats_item, dict) else {}
                if isinstance(stats_item, dict):
                    for k, lbl in (("negative", "负面"), ("positive", "正面"), ("neutral", "中性")):
                        if stats_item.get(k) is not None:
                            row[lbl] = _text(stats_item.get(k))
                trend_rows.append(row)
    elif isinstance(news_trend, list):
        for ti in news_trend:
            if isinstance(ti, dict):
                row = {"周期/月份": _text(ti.get("month"))}
                raw_stats_item = ti.get("stats")
                stats_item = raw_stats_item if isinstance(raw_stats_item, dict) else {}
                for k, lbl in (("negative", "负面"), ("positive", "正面"), ("neutral", "中性")):
                    if stats_item.get(k) is not None:
                        row[lbl] = _text(stats_item.get(k))
                trend_rows.append(row)

    # 全文检索资讯表（原 information_industry_news 已下线，改用 information_search）
    industry_rows = _news_rows(industry_news, title_key="informationTitle")
    industry_total = industry_news.get("total") if isinstance(industry_news, dict) else None

    # 主题跟踪表
    topic_rows = _news_rows(topic_news, title_key="informationTitle")
    topic_total = topic_news.get("total") if isinstance(topic_news, dict) else None

    # 关联共现企业聚合（来源：company_news.resultList[].relatedEnterprises）
    subject_enterprise = opts.get("enterprise") or ""
    related_rows = _related_enterprises_rows(company_news, exclude_name=subject_enterprise)

    title_counts: Dict[str, int] = {}
    for row in company_rows:
        title = row.get("标题") or "-"
        if title and title != "-":
            title_counts[title] = title_counts.get(title, 0) + 1
    repost_kv = {
        "样本条数": len(company_rows),
        "标题完全一致的重复记录": sum(n - 1 for n in title_counts.values() if n > 1),
        "去重后标题数": len(title_counts),
        "说明": "仅按标题完全一致识别疑似转载/重复收录；近义标题、改标题转载及同一事件的多次进展未合并。",
    }

    sections = [
        {"key": "company_news_statistics", "title": "企业资讯统计", "kind": "kv", "note": "情感分布（正/负/中/未知）；情感为上游模型标签"},
        {"key": "sentiment_dist", "title": "资讯情感分布", "kind": "donut", "note": "按情感类别统计资讯数量占比",
         "chart": {"name": "情感", "value": "数量"}, "columns": [("情感", "情感"), ("数量", "数量")]},
        {"key": "sentiment_trend", "title": "舆情情感趋势", "kind": "multi_line", "note": "按月份统计情感分布",
         "chart": {"x": "周期/月份", "series": ["负面", "正面", "中性"], "area": False},
         "columns": [("周期/月份", "周期/月份"), ("负面", "负面"), ("正面", "正面"), ("中性", "中性")]},
        {"key": "company_news", "title": "企业资讯明细", "kind": "table",
         "note": f"命中 {company_total if company_total is not None else '未返回总数'} 条" + (f"；明细筛选：情感={_SENTIMENT_LABEL_MAP.get(_int(opts.get('sentiment')), '未知')}" if opts.get("sentiment") is not None else ""),
         "columns": [("标题", "标题"), ("来源", "来源"), ("发布时间", "发布时间"), ("情感", "情感"), ("链接", "链接"), ("简介", "简介")]},
        {"key": "repost_summary", "title": "重复与转载提示", "kind": "kv", "note": "仅按企业资讯样本的标题完全一致识别，不等同于事件级去重"},
        {"key": "related_enterprises", "title": "关联共现企业", "kind": "table",
         "note": "企业资讯样本中高频共现的关联实体（仅按全/半角括号与空白差异排除主体自身；其他名称不合并；最多展示前 15 个）",
         "columns": [("企业名称", "企业名称"), ("类型", "类型"), ("共现次数", "共现次数")]},
        {"key": "industry_news", "title": "全文检索资讯", "kind": "table",
         "note": f"命中 {industry_total if industry_total is not None else '未返回总数'} 条（全文检索口径，非企业全量）",
         "columns": [("标题", "标题"), ("来源", "来源"), ("发布时间", "发布时间"), ("情感", "情感"), ("链接", "链接"), ("简介", "简介")]},
        {"key": "topic_news", "title": "资讯主题跟踪", "kind": "table",
         "note": f"命中 {topic_total if topic_total is not None else '未返回总数'} 条（与全文检索同源同参，复用同一批检索结果）",
         "columns": [("标题", "标题"), ("来源", "来源"), ("发布时间", "发布时间"), ("情感", "情感"), ("链接", "链接"), ("简介", "简介")]},
    ]

    # Derive sentiment distribution rows from stats_kv (情感 -> 数量).
    sentiment_dist_rows: List[Dict[str, Any]] = []
    for label in ("正面", "负面", "中性", "未知"):
        v = stats_kv.get(label)
        try:
            n = float(str(v)) if v is not None else None
        except (TypeError, ValueError):
            n = None
        if n and n > 0:
            sentiment_dist_rows.append({"情感": label, "数量": str(int(n))})

    return {
        "sections": sections,
        "company_news_statistics": stats_kv,
        "sentiment_dist": sentiment_dist_rows,
        "sentiment_trend": trend_rows,
        "company_news": company_rows,
        "repost_summary": repost_kv,
        "related_enterprises": related_rows,
        "industry_news": industry_rows,
        "topic_news": topic_rows,
    }


def build_records(core: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for item in core.get("company_news") or []:
        out.append({
            "标题": item.get("标题") or "-",
            "来源": item.get("来源") or "-",
            "发布时间": item.get("发布时间") or "-",
            "情感": item.get("情感") or "-",
        })
    return out[:20]


def _sentiment_ratio(stats_kv: Mapping[str, Any]) -> Dict[str, Any]:
    """Compute positive/negative/neutral counts, shares and net sentiment ratio."""
    counts: Dict[str, float] = {}
    for k in ("正面", "负面", "中性", "未知"):
        v = stats_kv.get(k)
        try:
            counts[k] = float(str(v)) if v is not None else 0.0
        except (TypeError, ValueError):
            counts[k] = 0.0
    total = sum(counts.values())
    if not total:
        return {}
    pos = counts.get("正面", 0.0)
    neg = counts.get("负面", 0.0)
    return {
        "total": total,
        "pos": pos, "neg": neg, "neu": counts.get("中性", 0.0),
        "pos_share": pos / total * 100,
        "neg_share": neg / total * 100,
        "net_ratio": (pos - neg) / total * 100,  # net sentiment
    }


def _month_index(value: Any) -> Optional[int]:
    text = _text(value)
    if len(text) < 7 or text[4] not in "-/":
        return None
    try:
        return int(text[:4]) * 12 + int(text[5:7]) - 1
    except (TypeError, ValueError):
        return None


def _trend_series_analysis(rows: Sequence[Mapping[str, Any]], value_key: str, as_of_month: Optional[int] = None) -> Dict[str, Any]:
    """Direction/peak for a monthly series, with defensible data-quality guards.

    Drops the current partial month, requires >=3 data months and >=5 items in
    each of the last two months, and skips series whose latest data is more
    than 2 months old. Non-consecutive months are labeled as a comparison with
    the previous available month, not as month-over-month change.
    """
    points: List[tuple[Any, float, Optional[int]]] = []
    for r in rows:
        try:
            n = float(str(r.get(value_key, 0)).replace(",", ""))
        except (TypeError, ValueError):
            n = 0.0
        points.append((r.get("周期/月份", "-"), n, _month_index(r.get("周期/月份"))))
    if not points:
        return {}

    partial_period = None
    if as_of_month is not None:
        complete = [p for p in points if p[2] != as_of_month]
        if len(complete) >= 2 and len(complete) < len(points):
            partial_period = _text(points[-1][0])
            points = complete
    if len(points) < 3:
        return {"insufficient": "有数据的月份不足 3 期，未作趋势研判", "partial_period": partial_period}

    last_period, last_n, last_idx = points[-1]
    prev_period, prev_n, prev_idx = points[-2]
    if as_of_month is not None and last_idx is not None and last_idx < as_of_month - 2:
        return {"insufficient": f"最新数据止于 {_text(last_period)}，距报告期超过 2 个月，不作近月趋势研判", "partial_period": partial_period}
    if min(last_n, prev_n) < 5:
        return {"insufficient": "近两个有数据月份数量过少（<5 条/月），未作趋势研判", "partial_period": partial_period}

    peak_idx = max(range(len(points)), key=lambda i: points[i][1])
    pct = (last_n - prev_n) / prev_n * 100 if prev_n > 0 else 0.0
    direction = "基本持平"
    yoy = ""
    if abs(pct) > 5:
        direction = f"{'上升' if pct > 0 else '下降'} {abs(pct):.0f}%"
        compare = "环比" if (last_idx is not None and prev_idx is not None and last_idx - prev_idx == 1) else "较上一有数据月份"
        verb = "上升" if pct > 0 else "下降"
        yoy = f"{compare}{verb} {abs(pct):.0f}%"
    return {
        "peak_period": _text(points[peak_idx][0]),
        "peak_value": points[peak_idx][1],
        "direction": direction,
        "yoy": yoy,
        "last": last_n,
        "compare_period": _text(last_period),
        "base_period": _text(prev_period),
        "partial_period": partial_period,
    }


def build_insights(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]], as_of_month: Optional[int] = None) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    metric_map = {m["label"]: str(m["value"]) for m in metrics}
    stats_kv = core.get("company_news_statistics") or {}
    trend_rows = core.get("sentiment_trend") or []

    # 1. 资讯曝光度
    if metric_map.get("企业资讯数"):
        insights.append({
            "feature": "资讯曝光度",
            "evidence": f"企业资讯命中 {metric_map.get('企业资讯数')} 条。",
            "interpretation": "资讯命中量仅描述检索口径内的样本数量，不直接代表品牌影响力或公众关注度。",
        })

    # 2. 情感结构（正/负占比 + 净情感）
    sr = _sentiment_ratio(stats_kv)
    if sr:
        insights.append({
            "feature": "情感结构与净声量",
            "evidence": f"正面 {int(sr['pos'])}（{sr['pos_share']:.0f}%）、负面 {int(sr['neg'])}（{sr['neg_share']:.0f}%）、中性 {int(sr['neu'])}；净情感 {sr['net_ratio']:+.0f}%。",
            "interpretation": "情感比例是算法分类结果，应结合原文抽样核验；不能据此直接判定企业声誉健康或风险等级。",
        })

    # 3. 资讯体量趋势（按月汇总正面+负面+中性 → 总声量趋势）
    if trend_rows:
        total_series = []
        for r in trend_rows:
            tot = 0.0
            for k in ("正面", "负面", "中性"):
                try:
                    tot += float(str(r.get(k, 0)).replace(",", ""))
                except (TypeError, ValueError):
                    pass
            total_series.append({"周期/月份": r.get("周期/月份", "-"), "数量": tot})
        ta = _trend_series_analysis(total_series, "数量", as_of_month)
        if ta and not ta.get("insufficient") and ta.get("direction") != "基本持平":
            extra = f"；{ta['partial_period']} 为不完整月份，未纳入比较" if ta.get("partial_period") else ""
            insights.append({
                "feature": "资讯声量月度变化",
                "evidence": f"声量峰值出现在“{ta['peak_period']}”（{ta['peak_value']:.0f} 条）；{ta['compare_period']} 与 {ta['base_period']} 相比，{ta.get('yoy') or ta['direction']}{extra}。",
                "interpretation": "该变化仅描述上游返回的月度样本条数，样本量小时波动很大；不能单独解释为关注度上升或话题冷却。",
            })

    # 4. 负面趋势研判（负面声量走向）
    if trend_rows and any(_to_float(r.get("负面")) for r in trend_rows):
        nta = _trend_series_analysis(trend_rows, "负面", as_of_month)
        if nta and not nta.get("insufficient") and nta.get("peak_value", 0) > 0:
            extra = f"；{nta['partial_period']} 为不完整月份，未纳入比较" if nta.get("partial_period") else ""
            insights.append({
                "feature": "负面标签月度变化",
                "evidence": f"负面标签峰值出现在“{nta['peak_period']}”（{nta['peak_value']:.0f} 条）；{nta['compare_period']} 与 {nta['base_period']} 相比，{nta.get('yoy') or nta['direction']}{extra}。",
                "interpretation": "负面条数变化仅描述上游情感标签的月度样本；下降原因无法由数量判断，仍需核验事件、时间窗口与转载去重。",
            })

    # 企业资讯与全文检索使用不同产品、查询范围和时间口径，禁止相除派生份额。
    if metric_map.get("行业资讯数") and metric_map.get("企业资讯数"):
        insights.append({
            "feature": "检索口径说明",
            "evidence": f"企业资讯产品命中 {metric_map['企业资讯数']} 条；独立全文检索命中 {metric_map['行业资讯数']} 条。",
            "interpretation": "两者来自不同产品与查询口径，仅并列披露，不计算行业份额、增长率或覆盖比例。",
        })

    # 6. 关联共现企业（资讯中高频同现的实体）
    related_rows = core.get("related_enterprises") or []
    if len(related_rows) >= 2:
        top = related_rows[:3]
        names = "、".join(f"{r.get('企业名称', '-')}" for r in top)
        total_co = sum(_to_float(r.get("共现次数")) for r in related_rows)
        scope = f"高频共现实体（最多展示 {len(related_rows)} 个）" if len(related_rows) >= 15 else f"样本内共现实体 {len(related_rows)} 个"
        insights.append({
            "feature": "关联共现企业",
            "evidence": f"{scope}，Top3：{names}（这些展示实体合计共现 {int(total_co)} 次）。",
            "interpretation": "共现仅表示实体出现在同一资讯样本中，样本并非全量，不能据此认定合作、竞争或上下游关系。",
        })

    if any(core.get(key) for key in ("company_news", "industry_news", "topic_news")):
        repost = core.get("repost_summary") or {}
        duplicate_clause = ""
        if repost:
            duplicate_clause = f"企业资讯样本 {repost.get('样本条数', '-')} 条中，标题完全一致的重复记录 {repost.get('标题完全一致的重复记录', 0)} 条。"
        insights.append({
            "feature": "事件计数与跨产品重叠限制",
            "evidence": duplicate_clause + "全文检索、主题跟踪与企业资讯按各自产品口径返回记录，可能包含同题转载或跨产品相同记录。",
            "interpretation": "记录数不等于独立事件数，跨产品数量不可相加；仅识别了标题完全一致的重复，近义标题与跨产品同事件未合并。",
        })

    if not insights:
        insights.append({
            "feature": "数据完整性",
            "evidence": "部分维度未返回有效数据。",
            "interpretation": "建议核对匹配关键词是否为企业全称或合适主题词，或检查 MCP 连接与上游数据产品覆盖范围。",
        })
    return insights


def _to_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def build_abstract(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]) -> str:
    name = subject.get("enterprise") or subject.get("match_raw") or "目标对象"
    section_labels = {
        "company_news_statistics": "企业资讯情感统计",
        "sentiment_dist": "资讯情感分布",
        "sentiment_trend": "资讯情感趋势",
        "company_news": "企业资讯明细",
        "related_enterprises": "关联实体共现",
        "industry_news": "全文检索资讯",
        "topic_news": "主题跟踪资讯",
    }
    populated = [label for key, label in section_labels.items() if _has_evidence(core.get(key))]
    coverage = "、".join(populated) if populated else "无有效章节"
    if subject.get("subject_type") == "topic":
        parts = [f"本报告以“{name}”为主题检索对象。本次有效数据仅覆盖：{coverage}；未返回有效企业资讯明细或企业情感统计时，不生成企业主体结论。"]
    else:
        parts = [f"本报告以“{name}”为企业查询对象。本次有效数据覆盖：{coverage}。"]
    if metrics:
        kv = "、".join(f"{m['label']} {m['value']}" for m in metrics[:5])
        parts.append(f"关键指标包括：{kv}。")
    parts.append("各产品记录按自身口径披露，记录数不等于独立事件数，跨产品数量不可相加。")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Dry-run sample
# --------------------------------------------------------------------------- #

def build_dry_run_payload(raw: str, keyword_type: str, opts: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        sample = load_json_file(SAMPLE_PATH)
    except Exception:
        sample = {}
    sample = sample if isinstance(sample, dict) else {}
    resolved = resolve_enterprise_name(raw)
    subject_sample = sample.get("subject") or {}
    subject = build_subject(raw, resolved, keyword_type, opts)
    # Preserve sample's resolved mapping (enterprise / resolve_reason) when present.
    if subject_sample.get("enterprise"):
        subject["enterprise"] = subject_sample["enterprise"]
        subject["matchKeyword"] = subject_sample["enterprise"]
    if subject_sample.get("resolve_reason"):
        subject["resolve_reason"] = subject_sample["resolve_reason"]
    core = sample.get("core_analysis") or {}
    metrics = sample.get("metrics") or []
    return apply_content_review(_assemble(subject, core, metrics, dry_run=True, opts=opts))


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #

def _content_quality_report(core: Mapping[str, Any]) -> Dict[str, Any]:
    """Section-fill rate from final declared sections and actual bodies.

    0 is populated; only None/""/[]/{} count as empty. Not an accuracy score.
    """
    ca = core if isinstance(core, dict) else {}
    sections = [s for s in (ca.get("sections") or []) if isinstance(s, dict) and s.get("key")]

    def filled(value: Any) -> bool:
        return value is not None and value != "" and value != [] and value != {}

    if sections:
        total = len(sections)
        populated = sum(1 for spec in sections if filled(ca.get(spec["key"])))
    else:
        keys = [k for k in ca if k != "sections"]
        total = max(1, len(keys))
        populated = sum(1 for key in keys if filled(ca.get(key)))
    return {
        "total_sections": total,
        "populated_sections": populated,
        "empty_sections": total - populated,
        "coverage_pct": round(populated / max(1, total) * 100),
    }


def _assemble(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]], *, dry_run: bool, opts: Mapping[str, Any]) -> Dict[str, Any]:
    abstract = build_abstract(subject, core, metrics)
    records = build_records(core)
    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    insights = build_insights(subject, core, metrics, _month_index(generated_at))
    quality_report = _content_quality_report(core)
    if quality_report["populated_sections"] == 0:
        import sys
        print("⚠️ 质量门禁警告: 所有核心分析维度均无数据", file=sys.stderr)
        target = subject.get("enterprise") or subject.get("match_raw") or "目标对象"
        abstract = f"本次对“{target}”的查询未获得有效数据；报告不据此生成资讯规模、情感或行业比较结论。请检查主体/主题、筛选条件及上游调用状态。"
    title = f"{subject.get('enterprise') or '目标对象'} 资讯大数据报告"
    report = {
        "report_type": REPORT_TYPE,
        "title": title,
        "banner": REPORT_BANNER,
        "subject": dict(subject),
        "abstract": abstract,
        "summary": abstract,
        "executive_summary": [item["interpretation"] for item in insights][:5] or [abstract[:120]],
        "metrics": list(metrics),
        "caliber": build_caliber(subject, opts),
        "core_analysis": dict(core),
        "representative_records": records,
        "insights": insights,
        "data_source": {
            "mcp_server": "information-mcp-server",
            "products": requested_products(subject),
            "generated_at": generated_at,
            "dry_run": dry_run,
            "quality_report": quality_report,
        },
    }
    return report


def _information_repost_summary(core: Mapping[str, Any]) -> Dict[str, Any]:
    rows = [r for r in (core.get("company_news") or []) if isinstance(r, dict)]
    title_counts: Dict[str, int] = {}
    for row in rows:
        title = _text(row.get("标题"))
        if title and title != "-":
            title_counts[title] = title_counts.get(title, 0) + 1
    return {
        "样本条数": len(rows),
        "标题完全一致的重复记录": sum(n - 1 for n in title_counts.values() if n > 1),
        "去重后标题数": len(title_counts),
        "说明": "仅按标题完全一致识别疑似转载/重复收录；近义标题、改标题转载及同一事件的多次进展未合并。",
    }


def apply_content_review(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Rebuild information narrative content from an existing payload.

    Pure/in-memory. Drops sample-scope metrics, adds an exact-title repost
    summary for the retained company-news sample, translates enum labels,
    normalizes related-entity types, rebuilds trend insights with partial-month
    / recency / low-volume guards, and refreshes abstract/executive_summary.
    """
    out = copy.deepcopy(dict(report))
    metrics: List[Dict[str, Any]] = []
    for metric in out.get("metrics") or []:
        if not isinstance(metric, dict) or metric.get("label") in SAMPLE_METRIC_LABELS:
            continue
        item = dict(metric)
        if item.get("label") in ("正面资讯", "负面资讯", "中性资讯"):
            item["hint"] = f"{item['label'].replace('资讯', '')}情感模型标签条数（未逐条人工核验）"
            if item.get("delta", "").startswith("占比"):
                item["delta"] = "标签" + item["delta"]
        metrics.append(item)
    out["metrics"] = metrics

    core = out.setdefault("core_analysis", {})
    if not core.get("repost_summary"):
        core["repost_summary"] = _information_repost_summary(core)
    sections = core.get("sections") or []
    if not any(isinstance(s, dict) and s.get("key") == "repost_summary" for s in sections):
        insert_at = next((i for i, s in enumerate(sections) if isinstance(s, dict) and s.get("key") == "company_news"), len(sections))
        sections.insert(insert_at + 1, {"key": "repost_summary", "title": "重复与转载提示", "kind": "kv", "note": "仅按企业资讯样本的标题完全一致识别，不等同于事件级去重"})
        core["sections"] = sections
    for spec in sections:
        if not isinstance(spec, dict):
            continue
        key = spec.get("key")
        note = str(spec.get("note") or "")
        if "sentimentLabel" in note:
            spec["note"] = re.sub(r"；?sentimentLabel=\d+（[^）]*）", "", note)
        if key == "related_enterprises":
            spec["note"] = "企业资讯样本中高频共现的关联实体（仅按全/半角括号与空白差异排除主体自身；其他名称不合并；最多展示前 15 个）"
        elif key == "industry_news":
            spec["note"] = re.sub(r"（information_search[^）]*）", "（全文检索口径，非企业全量）", note)
        elif key == "topic_news":
            spec["note"] = note.replace("复用同一批已付费数据", "复用同一批检索结果").replace("复用同一批已付费结果", "复用同一批检索结果")

    subject = out.get("subject") or {}
    subject_key = _self_entity_key(subject.get("enterprise") or "")
    deduped_related: Dict[str, Dict[str, Any]] = {}
    for row in core.get("related_enterprises") or []:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("企业名称"))
        if not name or (subject_key and _self_entity_key(name) == subject_key):
            continue
        # Exact raw name only; no speculative merging of legal entities.
        entry = deduped_related.setdefault(name, {
            "企业名称": name,
            "类型": _entity_type_text(row.get("类型")),
            "共现次数": 0,
        })
        entry["共现次数"] += int(_to_float(row.get("共现次数")))
    related_rows = sorted(deduped_related.values(), key=lambda r: r["共现次数"], reverse=True)[:15]
    core["related_enterprises"] = related_rows
    stats_kv = core.get("company_news_statistics") or {}
    if stats_kv.get("情感类别"):
        reverse_map = {"positive": "正面", "negative": "负面", "neutral": "中性", "unknown": "未知"}
        stats_kv["情感类别"] = "、".join(reverse_map.get(str(t).strip().lower(), _text(t)) for t in str(stats_kv["情感类别"]).replace("，", "、").replace(",", "、").split("、") if t)

    source = out.get("data_source") or {}
    insights = build_insights(subject, core, metrics, _month_index(source.get("generated_at")))
    out["insights"] = insights
    abstract = build_abstract(subject, core, metrics)
    out["abstract"] = abstract
    out["summary"] = abstract
    out["executive_summary"] = [item["interpretation"] for item in insights][:5] or [abstract[:120]]
    out["caliber"] = build_caliber(subject, {"sentiment": subject.get("sentiment_label"), "pub_start": subject.get("pub_date_begin"), "pub_end": subject.get("pub_date_end")})
    out.setdefault("data_source", {})["quality_report"] = _content_quality_report(core)
    return out


def _search_args_for(keyword: str, opts: Mapping[str, Any], page_size: int) -> Dict[str, Any]:
    args: Dict[str, Any] = {"matchKeyword": keyword, "pageSize": page_size}
    if opts.get("pub_start"):
        args["pubDateBegin"] = opts.get("pub_start")
    if opts.get("pub_end"):
        args["pubDateEnd"] = opts.get("pub_end")
    return args


@paid_call_scope
def build_payload(raw: str, keyword_type: str, opts: Mapping[str, Any], max_pages: int = 1) -> Dict[str, Any]:
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages 必须为正整数")
    resolved = resolve_enterprise_name(raw)
    enterprise = resolved["enterprise"]
    page_size = opts.get("page_size") or 50

    # 1. 企业资讯明细（matchKeyword=企业名称）
    company_args: Dict[str, Any] = {
        "matchKeyword": enterprise,
        "keywordType": keyword_type,
        "pageSize": page_size,
    }
    if opts.get("sentiment") is not None:
        company_args["sentimentLabel"] = opts.get("sentiment")
    company_news = collect_detail_pages(
        _safe_call, T_COMPANY_NEWS, company_args,
        get_rows=_first_list, get_total=_safe_total, is_error=_is_api_error,
        max_pages=max_pages,
    ) if enterprise else {"text": "查询数据为空"}
    company_total = _safe_total(company_news) if isinstance(company_news, dict) else None

    # 2. 企业资讯监控统计视图（matchKeyword=企业名称）
    monitor_view = opts.get("view") or DEFAULT_MONITOR_VIEW
    monitor_args: Dict[str, Any] = {
        "matchKeyword": enterprise,
        "view": "statistics",
        "keywordType": keyword_type,
    }
    monitor_stats = _safe_call(T_MONITOR, monitor_args) if enterprise else {"text": "查询数据为空"}

    # 3. 全文检索资讯（matchKeyword=关键词；同 raw）
    # NOTE: information_industry_news is a DEAD product (returns {error:"产品不存在",code:"11014"}).
    # Use information_search instead — same args, returns resultList with title/source/time/link.
    industry_args = _search_args_for(raw, opts, page_size)
    industry_news = collect_detail_pages(
        _safe_call, T_SEARCH, industry_args,
        get_rows=_first_list, get_total=_safe_total, is_error=_is_api_error,
        max_pages=max_pages,
    )
    industry_total = _safe_total(industry_news) if isinstance(industry_news, dict) else None

    # 4. 资讯主题跟踪（matchKeyword=关键词）
    # information_topic 与 information_search 复用同一上游产品（6a60928a935bb6a5c6bbd68f）
    # 且参数完全一致（matchKeyword/pubDate/pageIndex/pageSize）→ 复用已付费检索结果，不重复计费。
    topic_args = _search_args_for(raw, opts, page_size)
    if topic_args == industry_args:
        topic_news = industry_news
    else:
        topic_news = collect_detail_pages(
            _safe_call, T_TOPIC, topic_args,
            get_rows=_first_list, get_total=_safe_total, is_error=_is_api_error,
            max_pages=max_pages,
        )
    topic_total = _safe_total(topic_news) if isinstance(topic_news, dict) else None

    subject = build_subject(raw, resolved, keyword_type, opts)
    core_opts = {**opts, "enterprise": enterprise}
    core = build_core_analysis(company_news, monitor_stats, industry_news, topic_news, core_opts)
    metrics = build_metrics(company_total, industry_total, topic_total, monitor_stats)
    opts_full = {**opts, "view": monitor_view}
    report = _attach_call_status(
        _assemble(subject, core, metrics, dry_run=False, opts=opts_full),
        {"企业资讯": company_news, "企业资讯监控": monitor_stats, "资讯全文检索": industry_news, "资讯主题跟踪": topic_news},
    )
    report = apply_content_review(report)
    return attach_pagination(report, {"企业资讯": company_news, "资讯全文检索": industry_news, "资讯主题跟踪": topic_news})


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="Compose an information big-data report via the information MCP.")
    parser.add_argument("--enterprise", required=True, help="企业全称、关键词或主题词（企业资讯按企业名称直查；行业/主题按关键词检索）")
    parser.add_argument("--keyword-type", default="name", help="主体类型：name/nameId/regNumber/socialCreditCode（企业资讯工具）")
    parser.add_argument("--pub-start", default=None, help="发布时间起始日期（行业资讯/主题跟踪），如 2025-01-01")
    parser.add_argument("--pub-end", default=None, help="发布时间截止日期（行业资讯/主题跟踪），如 2025-06-30")
    parser.add_argument("--sentiment", default=None, choices=["0", "1", "2", "3"], help="企业资讯情感过滤：0=负面/1=正面/2=中性/3=未知")
    parser.add_argument("--view", default=None, choices=["details", "statistics"], help="企业资讯监控视图：details=明细/statistics=统计（默认）")
    parser.add_argument("--page-size", type=int, default=None, help="分页大小（最多 50）")
    parser.add_argument("--max-pages", type=int, default=1, help="各资讯明细接口最多付费翻页数（默认 1；仅在明确需要更多结论/证据时增大）")
    parser.add_argument("--dry-run", action="store_true", help="不调用真实 MCP，使用样例数据组装报告骨架")
    parser.add_argument("--output", help="输出 JSON 路径；省略则打印到 stdout")
    parser.add_argument("--report-output", help="同时输出 HTML 报告（.html）与 Markdown 报告（.md）")
    parser.add_argument("--pdf-output", help="额外输出 PDF 报告（.pdf）；需要 Playwright + Chromium")
    args = parser.parse_args()

    opts = {
        "pub_start": args.pub_start,
        "pub_end": args.pub_end,
        "sentiment": args.sentiment,
        "view": args.view,
        "page_size": args.page_size,
    }

    if not args.dry_run:
        if args.max_pages is not None and args.max_pages < 1:
            die("--max-pages 必须为正整数")

    if args.dry_run:
        payload = build_dry_run_payload(args.enterprise, args.keyword_type, opts)
    else:
        payload = build_payload(args.enterprise, args.keyword_type, opts, args.max_pages)

    payload = prepare_draft(payload)

    if args.output:
        out = pathlib.Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "json": str(out), "dry_run": args.dry_run})
    else:
        print_json(payload)

    if args.report_output:
        base_out = pathlib.Path(args.report_output).expanduser()
        base_out.parent.mkdir(parents=True, exist_ok=True)
        html_path = base_out.with_suffix(".html") if base_out.suffix.lower() not in (".html", ".htm") else base_out
        md_path = html_path.with_suffix(".md")
        html_path.write_text(render_html(payload), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        if args.pdf_output:
            pdf_path = pathlib.Path(args.pdf_output).expanduser()
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            html_to_pdf(render_html(payload), str(pdf_path))
        print_json({"ok": True, "html": str(html_path), "markdown": str(md_path), "pdf": str(pdf_path) if args.pdf_output else None, "dry_run": args.dry_run})


if __name__ == "__main__":
    main()
