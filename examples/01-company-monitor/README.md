# 企业资讯监控

- 用户需求：跟踪比亚迪股份有限公司的企业资讯、情感统计、全文检索和主题资讯。
- 决策用途：建立企业动态监控报告。
- 本轮结果：**本轮检查通过**
- 实际工具调用：4；失败 0
- 章节覆盖率：100%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 企业资讯与主题/全文检索结果分章节
- 情感统计按四类呈现
- 资讯标题、来源、时间与链接按源数据保留
- 企业名称查询与主题词查询口径应说明

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 资讯收录取决于数据源覆盖，不能视为全网完整监测。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 information-skill/scripts/compose_report.py --enterprise '比亚迪股份有限公司' --view statistics --page-size 10 --output information-skill/output/01-company-monitor/report.json --report-output information-skill/output/01-company-monitor/report.html
```

## 逐场景业务复核

已逐项读取 targeted-fix 后当前 JSON/HTML/Markdown/calls/result，并核对实际工具、Product ID 与报告来源范围。

- **pass** 企业资讯与主题/全文检索结果分章节：company_news、information_search、information_topic 分别映射企业明细/全文检索/主题章节。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 5131), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 13), ('information_topic', 'data', 10, 13)]；subject={'enterprise': '比亚迪股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '比亚迪股份有限公司', 'keywordType': 'name', 'match_raw': '比亚迪股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'statistics'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 5, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 情感统计按四类呈现：统计分列正面1540、负面156、中性3402、未知33。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 5131), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 13), ('information_topic', 'data', 10, 13)]；subject={'enterprise': '比亚迪股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '比亚迪股份有限公司', 'keywordType': 'name', 'match_raw': '比亚迪股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'statistics'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 5, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 资讯标题、来源、时间与链接按源数据保留：明细保留标题、来源、发布时间、链接。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 5131), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 13), ('information_topic', 'data', 10, 13)]；subject={'enterprise': '比亚迪股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '比亚迪股份有限公司', 'keywordType': 'name', 'match_raw': '比亚迪股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'statistics'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 5, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。
- **pass** 企业名称查询与主题词查询口径应说明：caliber 区分企业主体查询与全文/主题产品，并声明跨产品数量不可相加。 本轮 targeted-fix 实际证据：technical_status=passed，successful_data_calls=4，actual_calls=[('information_company_news', 'data', 10, 5131), ('information_monitor', 'data', None, None), ('information_search', 'data', 10, 13), ('information_topic', 'data', 10, 13)]；subject={'enterprise': '比亚迪股份有限公司', 'subject_type': 'enterprise', 'matchKeyword': '比亚迪股份有限公司', 'keywordType': 'name', 'match_raw': '比亚迪股份有限公司', 'resolved': True, 'resolve_reason': '视为企业全称', 'pub_date_begin': '', 'pub_date_end': '', 'sentiment_label': '', 'monitor_view': 'statistics'}；sections={'company_news_statistics': 5, 'sentiment_dist': 4, 'sentiment_trend': 12, 'company_news': 10, 'related_enterprises': 5, 'industry_news': 10, 'topic_news': 10}；products=[('企业资讯查询', '66b485eadaf8c77fb249a455'), ('企业资讯监控', '66b338e274bf098447db7efd'), ('资讯全文检索', '6a60928a935bb6a5c6bbd68f'), ('资讯主题跟踪', '6a60928a935bb6a5c6bbd68f')]；caliber.data_scope=企业资讯查询、企业资讯监控、资讯全文检索、资讯主题跟踪；quality={'total_sections': 7, 'populated_sections': 7, 'empty_sections': 0, 'coverage_pct': 100}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)
[页面截图](browser.png)