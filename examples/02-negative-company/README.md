# 企业负面资讯筛查

- 用户需求：筛选华为技术有限公司的负面企业资讯，并保留统计视图。
- 决策用途：提供需要人工阅读核实的负面信息线索。
- 本轮结果：**本轮检查通过**
- 实际工具调用：4；失败 0
- 章节覆盖率：100%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 企业资讯明细应按负面标签筛选
- 统计视图与明细过滤口径区别应写明
- 不得将负面标签当作事实认定

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 自动情感分类和转载内容都可能有误，必须核对原文。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 information-skill/scripts/compose_report.py --enterprise '华为技术有限公司' --sentiment 0 --view details --page-size 10 --output information-skill/output/02-negative-company/report.json --report-output information-skill/output/02-negative-company/report.html
```

## 逐场景业务复核

已逐项读取 targeted-fix 后当前 JSON/HTML/Markdown/calls/result，并核对实际工具、Product ID 与报告来源范围。

- **pass** 企业资讯明细应按负面标签筛选：company_news 请求 sentimentLabel=0；当前页记录按返回负面标签展示。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 307), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 15), ('information_topic', 'data', 10, 15)]；subject={'enterprise': '华为技术有限公司', 'subject_type': 'enterprise', 'matchKeyword': '华为技术有限公司', 'keywordType': 'name', 'match_raw': '华为技术有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '0', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 3, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 统计视图与明细过滤口径区别应写明：统计视图四类总量与负面明细筛选分别披露，不混用。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 307), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 15), ('information_topic', 'data', 10, 15)]；subject={'enterprise': '华为技术有限公司', 'subject_type': 'enterprise', 'matchKeyword': '华为技术有限公司', 'keywordType': 'name', 'match_raw': '华为技术有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '0', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 3, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 不得将负面标签当作事实认定：报告明确负面标签不能替代对原文事实的核验，下降也不代表应对有效。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 307), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 15), ('information_topic', 'data', 10, 15)]；subject={'enterprise': '华为技术有限公司', 'subject_type': 'enterprise', 'matchKeyword': '华为技术有限公司', 'keywordType': 'name', 'match_raw': '华为技术有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '0', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 3, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)