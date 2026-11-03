# 企业正面资讯抽样

- 用户需求：查看贵州茅台酒股份有限公司的正面企业资讯样本。
- 决策用途：观察正面内容来源和主题构成。
- 本轮结果：**本轮检查通过**
- 实际工具调用：4；失败 0
- 章节覆盖率：100%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 企业明细按正面标签筛选
- 来源数量不等同于实际传播效果
- 情感统计与筛选明细口径需区分

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 正面标签不能证明内容真实或代表公众总体态度。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 information-skill/scripts/compose_report.py --enterprise '贵州茅台酒股份有限公司' --sentiment 1 --view details --page-size 8 --output information-skill/output/06-positive-company/report.json --report-output information-skill/output/06-positive-company/report.html
```

## 逐场景业务复核

已逐项读取 targeted-fix 后当前 JSON/HTML/Markdown/calls/result，并核对实际工具、Product ID 与报告来源范围。

- **pass** 企业明细按正面标签筛选：company_news 请求 sentimentLabel=1，当前页8条按正面标签返回。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 8, 776), ('information_monitor', 'data', None, None), ('information_search', 'data', 8, 8), ('information_topic', 'data', 8, 8)]；subject={'enterprise': '贵州茅台酒股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '贵州茅台酒股份有限公司', 'keywordType': 'name', 'match_raw': '贵州茅台酒股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '1', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 8, 'related_enterprises': 6, 'industry_news': 8, 'topic_news': 8}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 来源数量不等同于实际传播效果：来源数6仅描述样本来源分布，报告明确不等同实际传播效果。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 8, 776), ('information_monitor', 'data', None, None), ('information_search', 'data', 8, 8), ('information_topic', 'data', 8, 8)]；subject={'enterprise': '贵州茅台酒股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '贵州茅台酒股份有限公司', 'keywordType': 'name', 'match_raw': '贵州茅台酒股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '1', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 8, 'related_enterprises': 6, 'industry_news': 8, 'topic_news': 8}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 情感统计与筛选明细口径需区分：正面统计776与正面筛选明细分别展示，跨产品/口径数量不相加。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 8, 776), ('information_monitor', 'data', None, None), ('information_search', 'data', 8, 8), ('information_topic', 'data', 8, 8)]；subject={'enterprise': '贵州茅台酒股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '贵州茅台酒股份有限公司', 'keywordType': 'name', 'match_raw': '贵州茅台酒股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '1', 'monitor_view': 'details'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 8, 'related_enterprises': 6, 'industry_news': 8, 'topic_news': 8}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)