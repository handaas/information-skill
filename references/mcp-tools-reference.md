# MCP 工具参考 — information-mcp-server

本 skill 连接的 MCP server：`handaas-mcp-server/information-mcp-server`（“资讯大数据”）。

> **重要**：information MCP 采用 newer-style 工具，通过 `view` 等 Literal 选择器路由到不同上游数据源，**单次工具调用不会默认触发多个计费接口**。无独立的 fuzzy_search 工具。工具按匹配语义分两类：
> - **企业类**（`information_company_news` / `information_monitor`）：`matchKeyword` 为企业标识，配合 `keywordType`。
> - **关键词类**（`information_search` / `information_industry_news` / `information_topic`）：`matchKeyword` 为搜索/行业/主题关键词。

## 通用约定

- `keywordType` 枚举（企业类工具）：`name`（企业名称）/ `nameId`（企业 id）/ `regNumber`（注册号）/ `socialCreditCode`（统一社会信用代码）。
- `sentimentLabel` 枚举：`0`=负面 / `1`=正面 / `2`=中性 / `3`=未知。
- 分页：`pageIndex` 从 1 开始；`pageSize` 单页最多 50。
- 检索类工具支持 `pubDateBegin` / `pubDateEnd`（发布区间）。

---

## 工具清单

### 1. `information_search` — 资讯全文检索

用途：按关键词搜索新闻资讯标题和正文（按主题/事件/话题）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 搜索关键词（主题/事件，非企业标识） |
| `pubDateBegin` | string | 否 | 发布时间起始日期 |
| `pubDateEnd` | string | 否 | 发布时间截止日期 |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `pageSize` | int | 否 | 最大 50（默认 20） |
| `includeContent` | bool | 否 | 是否返回正文（默认 false；标题/链接/来源/时间始终返回） |
| `contentMaxChars` | int | 否 | 返回正文时每条最多保留字符数（默认 1000，最大 5000） |

返回（`total` + `resultList`）：每条含 informationTitle、informationSource、informationPublishTime、informationText（按需）、链接、sentimentLabel 等。

product_id：`6a60928a935bb6a5c6bbd68f`。

---

### 2. `information_company_news` — 企业资讯查询

用途：查询指定企业的新闻舆情明细。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业名称/企业 id/注册号/统一社会信用代码 |
| `keywordType` | Literal | 否 | 主体类型（默认 name） |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `pageSize` | int | 否 | 最大 50（默认 50） |
| `sentimentLabel` | Literal | 否 | 0=负面/1=正面/2=中性/3=未知 |

返回（`total` + `resultList`）：新闻简介、链接、来源、标题、发布时间、相关企业、情感标签。

product_id：`66b485eadaf8c77fb249a455`。

---

### 3. `information_industry_news` — 行业资讯检索

用途：按行业、赛道或产业关键词检索资讯（行业研究与市场动态）。不用于按企业标识查询舆情。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 行业/赛道/产业关键词 |
| `pubDateBegin` | string | 否 | 发布时间起始日期 |
| `pubDateEnd` | string | 否 | 发布时间截止日期 |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `pageSize` | int | 否 | 最大 50（默认 20） |
| `includeContent` | bool | 否 | 是否返回正文 |
| `contentMaxChars` | int | 否 | 正文截断长度 |

返回：同 `information_search`（复用全域资讯搜索 API）。

product_id：`6a60928a935bb6a5c6bbd68f`（复用全域资讯搜索）。

---

### 4. `information_topic` — 资讯主题跟踪

用途：跟踪政策、技术、品牌、热点事件等明确主题（聚焦具体主题，区别于宽泛行业）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 主题/事件关键词 |
| `pubDateBegin` | string | 否 | 发布时间起始日期 |
| `pubDateEnd` | string | 否 | 发布时间截止日期 |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `pageSize` | int | 否 | 最大 50（默认 20） |
| `includeContent` | bool | 否 | 是否返回正文 |
| `contentMaxChars` | int | 否 | 正文截断长度 |

返回：同 `information_search`（复用全域资讯搜索 API）。

product_id：`6a60928a935bb6a5c6bbd68f`（复用全域资讯搜索）。

---

### 5. `information_monitor` — 企业资讯动态监控

用途：监控企业资讯动态，可选择明细或情感趋势统计视图（单次调用只访问所选视图对应的一个 product id）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业名称/企业 id/注册号/统一社会信用代码 |
| `view` | Literal | 否 | `details`=新闻事件明细 / `statistics`=情感分布与趋势（默认） |
| `keywordType` | Literal | 否 | 主体类型（默认 name） |
| `pageIndex` | int | 否 | 从 1 开始（默认 1；details 视图） |
| `pageSize` | int | 否 | 最大 50（默认 50；details 视图） |
| `sentimentLabel` | Literal | 否 | 0=负面/1=正面/2=中性/3=未知（details 视图） |

返回：`details`→同 `information_company_news`；`statistics`→`newsSentimentStats`（情感分布 dict）、`sentimentLabelList`、`newsSentimentTrend`（趋势：month + stats{negative/positive}）。

product_id：`details`→`66b485eadaf8c77fb249a455`；`statistics`→`66b338e274bf098447db7efd`。

---

## 推荐调用顺序（报告编排）

1. `information_company_news`（matchKeyword=企业全称，keywordType=name）→ 企业资讯明细。
2. `information_monitor`（view=statistics）→ 情感分布与趋势统计。
3. `information_industry_news`（matchKeyword=行业关键词）→ 行业资讯。
4. `information_topic`（matchKeyword=主题关键词）→ 主题跟踪。

> 企业类工具入参为企业主体；行业/主题类工具入参为关键词。单次报告通常调用 3-4 个工具。
