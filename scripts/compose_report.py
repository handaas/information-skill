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
import datetime as dt
import json
import pathlib
import sys
from typing import Any, Dict, List, Mapping, Optional

from common import REPORT_BANNER, REPORT_TYPE, json_dumps, load_json_file, print_json
import mcp_client
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


def _is_api_error(value: Any) -> bool:
    """Detect MCP API error responses (not empty data, but actual failures like 405)."""
    if value is None:
        return False
    if isinstance(value, str):
        return any(s in value for s in ("接口调用失败", "查询失败", "状态码：4", "状态码：5"))
    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, str) and any(s in v for s in ("接口调用失败", "查询失败", "状态码：4", "状态码：5")):
                return True
    return False

def _first_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if _is_api_error(value):
            return []
        for key in ("resultList", "list", "items", "data"):
            if isinstance(value.get(key), list):
                return value[key]
    if value in (None, "", {}):
        return []
    return [value]


def _first_record(value: Any) -> Dict[str, Any]:
    for record in _first_list(value):
        if isinstance(record, dict):
            return record
    if isinstance(value, dict):
        return value
    return {}


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
        result = mcp_client.call_tool(tool, arguments)
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
        return {"keyword": "", "enterprise": "", "resolved": False, "reason": "关键词为空"}
    if any(suffix in raw for suffix in ("公司", "集团", "有限", "院", "厂", "中心", "事务所", "合作社", "合伙")):
        return {"keyword": raw, "enterprise": raw, "resolved": True, "reason": "视为企业全称"}
    return {"keyword": raw, "enterprise": raw, "resolved": True, "reason": "按关键词/企业名称直查（无模糊查询工具）"}


def _derive_core_metrics(metrics: List[Dict[str, Any]], core: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Derive additional metrics from core analysis sections."""
    sentiment = core.get("sentiment_dist", []) if isinstance(core, dict) else []
    trend = core.get("sentiment_trend", []) if isinstance(core, dict) else []
    news = core.get("company_news", []) if isinstance(core, dict) else []
    if isinstance(sentiment, list) and sentiment:
        try:
            total = sum(int(r.get("数量", 0)) for r in sentiment if str(r.get("数量", "0")).isdigit())
            positive = sum(int(r.get("数量", 0)) for r in sentiment if "正面" in str(r.get("情感", "")) and str(r.get("数量", "0")).isdigit())
            if total > 0:
                metrics.append({"label": "正面占比", "value": f"{positive/total*100:.1f}%", "hint": "正面资讯占总资讯比例"})
        except (ValueError, TypeError):
            pass
    if isinstance(trend, list) and trend:
        metrics.append({"label": "舆情监控周期", "value": str(len(trend)), "hint": "有情感数据的月份数"})
    if isinstance(news, list) and news:
        sources = set(str(r.get("来源", "")) for r in news if r.get("来源"))
        if sources:
            metrics.append({"label": "资讯来源数", "value": str(len(sources)), "hint": "不同媒体/来源数"})
        try:
            from collections import Counter
            src_counts = Counter(str(r.get("来源", "")) for r in news if r.get("来源"))
            if src_counts:
                top_src = src_counts.most_common(1)[0]
                metrics.append({"label": "高频来源", "value": f"{top_src[0]}（{top_src[1]}篇）", "hint": "报道最多的媒体来源"})
        except Exception:
            pass
    return metrics


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #

def build_subject(raw: str, resolved: Mapping[str, Any], keyword_type: str, opts: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "enterprise": resolved.get("enterprise") or raw,
        "matchKeyword": resolved.get("enterprise") or raw,
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
    sentiment_stats = s.get("newsSentimentStats") if isinstance(s.get("newsSentimentStats"), dict) else {}
    label_map = {"positive": "正面", "negative": "负面", "neutral": "中性", "unknown": "未知"}
    # Pre-compute shares for delta annotations.
    total_sent = 0.0
    sent_counts: Dict[str, float] = {}
    for key in ("positive", "negative", "neutral", "unknown"):
        try:
            n = float(sentiment_stats.get(key))
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


def build_caliber(subject: Mapping[str, Any], opts: Mapping[str, Any]) -> Dict[str, Any]:
    sentiment_hint = ""
    if opts.get("sentiment"):
        sentiment_hint = f"；sentimentLabel={opts.get('sentiment')}"
    date_hint = ""
    if opts.get("pub_start") or opts.get("pub_end"):
        date_hint = f"；发布区间 {opts.get('pub_start') or '不限'}~{opts.get('pub_end') or '不限'}"
    return {
        "match_target": subject.get("enterprise") or subject.get("match_raw"),
        "match_type": f"企业资讯按企业主体匹配（keywordType={subject.get('keywordType', 'name')}）；行业/主题/全文检索按关键词匹配{sentiment_hint}{date_hint}",
        "data_scope": "企业资讯明细、企业资讯情感统计、行业资讯、资讯主题跟踪",
        "products": ["资讯全文检索", "企业资讯查询", "行业资讯检索", "资讯主题跟踪", "企业资讯监控"],
        "limit": "数据来自公开新闻资讯；情感分布与趋势可能受数据源覆盖与更新延迟影响。",
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


def _related_enterprises_rows(payload: Any, *, exclude_name: str = "") -> List[Dict[str, Any]]:
    """Aggregate co-mentioned enterprises from resultList[].relatedEnterprises.
    Returns top entities by co-occurrence count: {企业名称, 类型, 共现次数}."""
    counter: Dict[str, Dict[str, Any]] = {}
    exclude_norm = (exclude_name or "").strip()
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
            if not name or name == exclude_norm:
                continue
            entry = counter.setdefault(name, {"企业名称": name, "类型": _text(ent.get("entityType")) or "-", "共现次数": 0})
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
    s = monitor_stats if isinstance(monitor_stats, dict) and not _is_error(monitor_stats) else {}
    sentiment_stats = s.get("newsSentimentStats") if isinstance(s.get("newsSentimentStats"), dict) else {}
    label_map = {"positive": "正面", "negative": "负面", "neutral": "中性", "unknown": "未知"}
    for key in ("positive", "negative", "neutral", "unknown"):
        val = sentiment_stats.get(key)
        if val is not None:
            stats_kv[label_map[key]] = _text(val)
    if isinstance(s.get("sentimentLabelList"), list) and s["sentimentLabelList"]:
        stats_kv["情感类别"] = "、".join(_text(t) for t in s["sentimentLabelList"] if t)
    # 趋势
    trend_rows: List[Dict[str, Any]] = []
    news_trend = s.get("newsSentimentTrend")
    if isinstance(news_trend, dict):
        months = news_trend.get("month")
        if isinstance(months, list):
            stats_dict = news_trend.get("stats") if isinstance(news_trend.get("stats"), list) else []
            for idx, m in enumerate(months):
                row = {"周期/月份": _text(m)}
                stats_item = stats_dict[idx] if idx < len(stats_dict) else {}
                if isinstance(stats_item, dict):
                    for k, lbl in (("negative", "负面"), ("positive", "正面"), ("neutral", "中性")):
                        if stats_item.get(k) is not None:
                            row[lbl] = _text(stats_item.get(k))
                trend_rows.append(row)
    elif isinstance(news_trend, list):
        for ti in news_trend:
            if isinstance(ti, dict):
                row = {"周期/月份": _text(ti.get("month"))}
                stats_item = ti.get("stats") if isinstance(ti.get("stats"), dict) else {}
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

    sections = [
        {"key": "company_news_statistics", "title": "企业资讯统计", "kind": "kv", "note": "情感分布（正/负/中/未知）"},
        {"key": "sentiment_dist", "title": "资讯情感分布", "kind": "donut", "note": "按情感类别统计资讯数量占比",
         "chart": {"name": "情感", "value": "数量"}, "columns": [("情感", "情感"), ("数量", "数量")]},
        {"key": "sentiment_trend", "title": "舆情情感趋势", "kind": "multi_line", "note": "按月份统计情感分布",
         "chart": {"x": "周期/月份", "series": ["负面", "正面", "中性"], "area": False},
         "columns": [("周期/月份", "周期/月份"), ("负面", "负面"), ("正面", "正面"), ("中性", "中性")]},
        {"key": "company_news", "title": "企业资讯明细", "kind": "table",
         "note": f"命中 {company_total if company_total is not None else '若干'} 条" + (f"；sentimentLabel={opts.get('sentiment')}" if opts.get("sentiment") else ""),
         "columns": [("标题", "标题"), ("来源", "来源"), ("发布时间", "发布时间"), ("情感", "情感"), ("链接", "链接"), ("简介", "简介")]},
        {"key": "related_enterprises", "title": "关联共现企业", "kind": "table",
         "note": "企业资讯中高频共现的关联实体（来源：relatedEnterprises，已排除自身）",
         "columns": [("企业名称", "企业名称"), ("类型", "类型"), ("共现次数", "共现次数")]},
        {"key": "industry_news", "title": "全文检索资讯", "kind": "table",
         "note": f"命中 {industry_total if industry_total is not None else '若干'} 条（information_search 全文检索）",
         "columns": [("标题", "标题"), ("来源", "来源"), ("发布时间", "发布时间"), ("情感", "情感"), ("链接", "链接"), ("简介", "简介")]},
        {"key": "topic_news", "title": "资讯主题跟踪", "kind": "table",
         "note": f"命中 {topic_total if topic_total is not None else '若干'} 条",
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


def _trend_series_analysis(rows: List[Mapping[str, Any]], value_key: str) -> Dict[str, Any]:
    """Direction/peak/YoY for a single sentiment series across months."""
    nums = []
    for r in rows:
        try:
            nums.append(float(str(r.get(value_key, 0)).replace(",", "")))
        except (TypeError, ValueError):
            nums.append(0.0)
    if not nums:
        return {}
    peak_idx = max(range(len(nums)), key=lambda i: nums[i])
    direction = "持平"
    yoy = ""
    if len(nums) >= 2:
        last, prev = nums[-1], nums[-2]
        if prev > 0:
            pct = (last - prev) / prev * 100
            if pct > 5:
                direction = f"上升 {pct:.0f}%"
            elif pct < -5:
                direction = f"下降 {abs(pct):.0f}%"
            yoy = f"环比 {pct:+.0f}%"
        elif last > 0 and prev == 0:
            direction = "由零转正"
    return {"peak_period": rows[peak_idx].get("周期/月份", "-"), "peak_value": nums[peak_idx], "direction": direction, "yoy": yoy, "last": nums[-1]}


def build_insights(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    metric_map = {m["label"]: str(m["value"]) for m in metrics}
    stats_kv = core.get("company_news_statistics") or {}
    trend_rows = core.get("sentiment_trend") or []

    # 1. 资讯曝光度
    if metric_map.get("企业资讯数"):
        insights.append({
            "feature": "资讯曝光度",
            "evidence": f"企业资讯命中 {metric_map.get('企业资讯数')} 条。",
            "interpretation": "资讯总量反映企业的媒体曝光与公众关注度，是品牌声量与舆情监测的基础指标。",
        })

    # 2. 情感结构（正/负占比 + 净情感）
    sr = _sentiment_ratio(stats_kv)
    if sr:
        health = "健康" if sr["neg_share"] < 15 else ("需关注" if sr["neg_share"] < 30 else "风险偏高")
        insights.append({
            "feature": "情感结构与净声量",
            "evidence": f"正面 {int(sr['pos'])}（{sr['pos_share']:.0f}%）、负面 {int(sr['neg'])}（{sr['neg_share']:.0f}%）、中性 {int(sr['neu'])}；净情感 {sr['net_ratio']:+.0f}%。",
            "interpretation": f"负面占比 {sr['neg_share']:.0f}%，舆情整体{health}；净情感为正说明正向声量主导，负面偏高时建议核查明细并启动预警。",
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
        ta = _trend_series_analysis(total_series, "数量")
        if ta and ta.get("direction") != "持平":
            insights.append({
                "feature": "资讯声量趋势",
                "evidence": f"声量峰值出现在“{ta['peak_period']}”（{ta['peak_value']:.0f} 条），近月{ta['direction']}，{ta.get('yoy', '')}。",
                "interpretation": "声量上升反映关注度走强（可能伴随产品发布/事件营销）；下降则可能是话题冷却或传播收尾。",
            })

    # 4. 负面趋势研判（负面声量走向）
    if trend_rows and any(_to_float(r.get("负面")) for r in trend_rows):
        nta = _trend_series_analysis(trend_rows, "负面")
        if nta and nta.get("peak_value", 0) > 0:
            insights.append({
                "feature": "负面舆情走向",
                "evidence": f"负面峰值出现在“{nta['peak_period']}”（{nta['peak_value']:.0f} 条），近月{nta['direction']}。",
                "interpretation": "负面声量上升需重点排查（产品质量/合规/公关事件）；下降说明应对有效或事件平息。",
            })

    # 5. 行业语境对比（企业声量 vs 行业声量）
    if metric_map.get("行业资讯数") and metric_map.get("企业资讯数"):
        try:
            ent_n = float(metric_map["企业资讯数"])
            ind_n = float(metric_map["行业资讯数"])
            if ind_n > 0:
                share = ent_n / ind_n * 100
                insights.append({
                    "feature": "行业语境对比",
                    "evidence": f"行业资讯命中 {metric_map['行业资讯数']} 条，企业资讯占行业声量约 {share:.1f}%。",
                    "interpretation": "企业声量份额反映其在行业中的话语权；份额偏低可结合公关投放与媒体合作提升曝光。",
                })
        except (TypeError, ValueError):
            pass

    # 6. 关联共现企业（资讯中高频同现的实体）
    related_rows = core.get("related_enterprises") or []
    if len(related_rows) >= 2:
        top = related_rows[:3]
        names = "、".join(f"{r.get('企业名称', '-')}" for r in top)
        total_co = sum(_to_float(r.get("共现次数")) for r in related_rows)
        insights.append({
            "feature": "关联共现企业",
            "evidence": f"共现实体 {len(related_rows)} 个，Top3：{names}（合计共现 {int(total_co)} 次）。",
            "interpretation": "高频共现企业反映与目标主体在同一新闻事件中反复出现的合作伙伴、竞争对手或上下游；集中度高通常意味着紧密的产业关联或事件相关性。",
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


def build_abstract(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: List[Mapping[str, Any]]) -> str:
    name = subject.get("enterprise") or subject.get("match_raw") or "目标对象"
    parts = [f"本报告以“{name}”为分析对象，基于公开新闻资讯，系统呈现企业资讯明细、企业资讯情感统计、行业资讯与资讯主题跟踪。"]
    if metrics:
        kv = "、".join(f"{m['label']} {m['value']}" for m in metrics[:5])
        parts.append(f"关键指标包括：{kv}。")
    parts.append("报告同时给出资讯曝光度、情感结构与行业语境的结构化解读，便于品牌公关、舆情监测与市场决策参考。")
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
    return _assemble(subject, core, metrics, dry_run=True, opts=opts)


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #

def _assemble(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: List[Mapping[str, Any]], *, dry_run: bool, opts: Mapping[str, Any]) -> Dict[str, Any]:
    abstract = build_abstract(subject, core, metrics)
    records = build_records(core)
    insights = build_insights(subject, core, metrics)
    # Quality gate: count populated core-analysis sections.
    ca = core if isinstance(core, dict) else {}
    secs = ca.get("sections", [])
    if secs:
        total_secs = len(secs)
        populated = sum(1 for s in secs if isinstance(s, dict) and ca.get(s.get("key")) not in (None, "", [], {}))
    else:
        total_secs = max(1, len([k for k in ca if k != "sections"]))
        populated = sum(1 for k in ca if k != "sections" and ca.get(k) not in (None, "", [], {}))
    quality_report = {
        "total_sections": total_secs,
        "populated_sections": populated,
        "empty_sections": total_secs - populated,
        "coverage_pct": round(populated / max(1, total_secs) * 100),
    }
    if populated == 0:
        import sys
        print("⚠️ 质量门禁警告: 所有核心分析维度均无数据", file=sys.stderr)
    title = f"{subject.get('enterprise') or '目标对象'} 资讯大数据报告"
    return {
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
            "products": [
                {"name": "资讯全文检索", "product_id": "6a60928a935bb6a5c6bbd68f"},
                {"name": "企业资讯查询", "product_id": "66b485eadaf8c77fb249a455"},
                {"name": "企业资讯监控", "product_id": "66b338e274bf098447db7efd"},
            ],
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "dry_run": dry_run,
            "quality_report": quality_report,
        },
    }


def _search_args_for(keyword: str, opts: Mapping[str, Any], page_size: int) -> Dict[str, Any]:
    args: Dict[str, Any] = {"matchKeyword": keyword, "pageIndex": 1, "pageSize": page_size}
    if opts.get("pub_start"):
        args["pubDateBegin"] = opts.get("pub_start")
    if opts.get("pub_end"):
        args["pubDateEnd"] = opts.get("pub_end")
    return args


def build_payload(raw: str, keyword_type: str, opts: Mapping[str, Any]) -> Dict[str, Any]:
    resolved = resolve_enterprise_name(raw)
    enterprise = resolved["enterprise"]
    page_size = opts.get("page_size") or 50

    # 1. 企业资讯明细（matchKeyword=企业名称）
    company_args: Dict[str, Any] = {
        "matchKeyword": enterprise,
        "keywordType": keyword_type,
        "pageIndex": 1,
        "pageSize": page_size,
    }
    if opts.get("sentiment"):
        company_args["sentimentLabel"] = opts.get("sentiment")
    company_news = _safe_call(T_COMPANY_NEWS, company_args)
    company_total = _safe_total(company_news) if isinstance(company_news, dict) else None

    # 2. 企业资讯监控统计视图（matchKeyword=企业名称）
    monitor_view = opts.get("view") or DEFAULT_MONITOR_VIEW
    monitor_args: Dict[str, Any] = {
        "matchKeyword": enterprise,
        "view": "statistics",
        "keywordType": keyword_type,
    }
    monitor_stats = _safe_call(T_MONITOR, monitor_args)

    # 3. 全文检索资讯（matchKeyword=关键词；同 raw）
    # NOTE: information_industry_news is a DEAD product (returns {error:"产品不存在",code:"11014"}).
    # Use information_search instead — same args, returns resultList with title/source/time/link.
    industry_args = _search_args_for(raw, opts, page_size)
    industry_news = _safe_call(T_SEARCH, industry_args)
    industry_total = _safe_total(industry_news) if isinstance(industry_news, dict) else None

    # 4. 资讯主题跟踪（matchKeyword=关键词）
    topic_args = _search_args_for(raw, opts, page_size)
    topic_news = _safe_call(T_TOPIC, topic_args)
    topic_total = _safe_total(topic_news) if isinstance(topic_news, dict) else None

    subject = build_subject(raw, resolved, keyword_type, opts)
    core_opts = {**opts, "enterprise": enterprise}
    core = build_core_analysis(company_news, monitor_stats, industry_news, topic_news, core_opts)
    metrics = build_metrics(company_total, industry_total, topic_total, monitor_stats)
    _derive_core_metrics(metrics, core if isinstance(core, dict) else {})
    opts_full = {**opts, "view": monitor_view}
    return _assemble(subject, core, metrics, dry_run=False, opts=opts_full)


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

    if args.dry_run:
        payload = build_dry_run_payload(args.enterprise, args.keyword_type, opts)
    else:
        payload = build_payload(args.enterprise, args.keyword_type, opts)

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
