# information-skill：已验收示例

本目录只展示 **4 个完全通过的真实正向场景**（最低要求4例）。

每例均为真实、非空、非缓存调用；技术检查、独立业务检查和离线浏览器检查全部通过。不把空数据、报错处理或仅生成页面计作通过。历史验收记录保留在本地 test-records/；本目录的 HTML/Markdown 由原 JSON 重渲染，不代表重新查询或重新验收。

| 场景 | 真实使用需求 | 报告 |
|---|---|---|
| [企业资讯监控](01-company-monitor/README.md) | 跟踪比亚迪股份有限公司的企业资讯、情感统计、全文检索和主题资讯。 | [HTML](01-company-monitor/report.html) / [MD](01-company-monitor/report.md) / [JSON](01-company-monitor/report.json) |
| [企业负面资讯筛查](02-negative-company/README.md) | 筛选华为技术有限公司的负面企业资讯，并保留统计视图。 | [HTML](02-negative-company/report.html) / [MD](02-negative-company/report.md) / [JSON](02-negative-company/report.json) |
| [企业正面资讯抽样](06-positive-company/README.md) | 查看贵州茅台酒股份有限公司的正面企业资讯样本。 | [HTML](06-positive-company/report.html) / [MD](06-positive-company/report.md) / [JSON](06-positive-company/report.json) |
| [企业资讯快报](07-compact-information/README.md) | 为腾讯科技（深圳）有限公司生成前 5 条资讯的管理层快报。 | [HTML](07-compact-information/report.html) / [MD](07-compact-information/report.md) / [JSON](07-compact-information/report.json) |

- [逐例验收结果](results.json) · [业务复核](review.json) · [证据摘要](evidence-index.json)
- 完整测试记录仅存于本地 test-records/live-replaced-20261027/（仅本地审计用，不随本目录发布），不属于可展示示例。
- 当前数据与结论限于原查询时点及公开样本；覆盖率不代表准确率或低风险。
