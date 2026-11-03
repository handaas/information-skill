# 企业资讯快报

- 用户需求：为腾讯科技（深圳）有限公司生成前 5 条资讯的管理层快报。
- 决策用途：验证小分页、统计与三种格式的一致性。
- 本轮结果：**本轮检查通过**
- 实际工具调用：4；失败 0
- 章节覆盖率：100%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 每类明细最多 5 条或实际返回数
- 总量和当前页样本不得混淆
- HTML、Markdown、JSON 的标题与来源一致

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 快报不是全量资讯档案。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 information-skill/scripts/compose_report.py --enterprise '腾讯科技（深圳）有限公司' --view details --page-size 5 --output information-skill/output/07-compact-information/report.json --report-output information-skill/output/07-compact-information/report.html
```

## 逐场景业务复核

已逐项读取 targeted-fix 后当前 JSON/HTML/Markdown/calls/result，并核对实际工具、Product ID 与报告来源范围。

- **pass** 每类明细最多 5 条或实际返回数：company_news当前页5条，search/topic各2条，均不超过pageSize=5或实际返回。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 5, 1859), ('information_monitor', 'data', None, None), ('information_search', 'data', 2, 2), ('information_topic', 'data', 2, 2)]；subject={'enterprise': '腾讯科技（深圳）有限公司', 'subject_type': 'enterprise', 'matchKeyword': '腾讯科技（深圳）有限公司', 'keywordType': 'name', 'match_raw': '腾讯科技（深圳）有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 5, 'related_enterprises': 15, 'industry_news': 2, 'topic_news': 2}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 总量和当前页样本不得混淆：企业资讯总量1859与当前页5条分开，全文/主题各自总量2也独立。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 5, 1859), ('information_monitor', 'data', None, None), ('information_search', 'data', 2, 2), ('information_topic', 'data', 2, 2)]；subject={'enterprise': '腾讯科技（深圳）有限公司', 'subject_type': 'enterprise', 'matchKeyword': '腾讯科技（深圳）有限公司', 'keywordType': 'name', 'match_raw': '腾讯科技（深圳）有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 5, 'related_enterprises': 15, 'industry_news': 2, 'topic_news': 2}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** HTML、Markdown、JSON 的标题与来源一致：独立重渲染通过，三种格式基于同一记录标题与来源。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 5, 1859), ('information_monitor', 'data', None, None), ('information_search', 'data', 2, 2), ('information_topic', 'data', 2, 2)]；subject={'enterprise': '腾讯科技（深圳）有限公司', 'subject_type': 'enterprise', 'matchKeyword': '腾讯科技（深圳）有限公司', 'keywordType': 'name', 'match_raw': '腾讯科技（深圳）有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 5, 'related_enterprises': 15, 'industry_news': 2, 'topic_news': 2}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)