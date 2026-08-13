---
name: information-report
description: Use for generating a professional information big-data report (资讯大数据报告) from the HandaaS information MCP — covering 企业资讯明细、企业资讯情感统计、行业资讯、资讯主题跟踪. Trigger when users ask for “资讯大数据报告”, “资讯分析报告”, “查一家公司的资讯”, “企业资讯监控”, “行业资讯”, “资讯主题跟踪”, “资讯检索”, or “企业舆情声量”. Infer the canonical enterprise name and topic keyword, pick the right MCP tools, and produce HTML + Markdown + JSON reports automatically.
---

# 资讯大数据报告

## 用户契约

把“资讯大数据报告”作为面向用户的调用短语。`information-report` 仅为内部包名。

当本 skill 处于激活状态：

1. 不要向用户索要 product_id、MCP 工具名、API 字段、内部参数或凭证信息；只接受企业名称、统一社会信用代码、注册号、企业 ID（企业资讯工具）或主题/行业关键词（检索类工具），以及可选的发布区间、情感过滤与监控视图。
2. 接受自然目标，例如“查一下某某公司的资讯”“监控这家企业的舆情动态”“检索某某行业的新闻”“跟踪某某主题的资讯”。
3. information MCP 工具无独立模糊查询；企业资讯工具按企业名称直查，行业/主题/全文检索按关键词直查。
4. 优先使用 MCP 连接（`INFORMATION_MCP_URL` Remote MCP 或本地 `handaas-mcp-server/information-mcp-server`）；不要让用户处理签名或凭证。
5. 同时产出 HTML（可分享交付）、Markdown（知识库 / wiki）、JSON（系统集成）三类产物。
6. 报告正文必须是专业研究报告风格：只见资讯事实与结构化数据，绝不出现工具名、入参、product_id、内部字段或空表。
7. 绝不打印 `secret_id`、`secret_key`、签名、token 或原始签名请求。
8. 默认 dry-run；真实付费 / 凭证调用需用户明确要求且 MCP 连接配置完整。
9. 数据为空时明确说明数据范围 / 口径，不渲染空表、不臆造事实。


- MCP 返回的嵌套 JSON 字符串（如金额 `{"coinType":"人民币","value":430000000.0}`、地址 `{"city":"杭州市",...}`）必须解析为可读文本（如"4.30 亿 人民币"、"浙江省杭州市"），绝不在报告正文、表格或指标中输出原始 JSON 字符串。
- 报告所有章节标题、指标卡标签必须用中文；`core_analysis.sections` 的 `title` 字段必须中文，不可显示英文 key（如 `holders`、`investments`）。
- 指标值必须可读化：金额格式为"X 亿/万 + 币种"，地址拼接省市区，比率显示百分号。详见 `references/report-output.md` 的「数据格式约束」。

## MCP 服务入口

- 上游 MCP 项目：`handaas-mcp-server/information-mcp-server`（位于 `HANDAAS_MCP_SERVER_ROOT` 或本仓库同级目录）。
- Remote MCP：设置环境变量 `INFORMATION_MCP_URL`（streamable-http），可选 `INFORMATION_MCP_TOKEN`。
- 本地 MCP：设置 `HANDAAS_MCP_SERVER_ROOT` 指向 `handaas-mcp-server` 仓库根目录；该 server 自己的 `.env` 提供 `INTEGRATOR_ID` / `SECRET_ID` / `SECRET_KEY`。
- 首次真实查询前，运行 `scripts/mcp_client.py ping` 与 `scripts/mcp_client.py list-tools` 验证连通。

## 按需加载 references

- 不清楚该 MCP 有哪些工具、参数、返回字段、何时调用：`references/mcp-tools-reference.md`。
- 报告结构、章节、质量底线、渲染工作流：`references/report-output.md`。

## 意图路由

| 用户意图 | 内部工作流 |
| --- | --- |
| 查一家公司的全维度资讯报告 | 调企业资讯 + 监控统计 + 行业 + 主题组装全量报告；`compose_report.py --enterprise ...` |
| 只要企业资讯明细 / 情感统计 | 仅调对应工具；监控统计用 `information_monitor --view statistics` |
| 按情感过滤企业资讯（负面/正面/中性/未知） | `compose_report.py --enterprise ... --sentiment 0\|1\|2\|3` |
| 检索行业资讯（按行业/赛道关键词） | `information_industry_news`，可用 `--pub-start/--pub-end` 限定区间 |
| 跟踪主题/事件资讯 | `information_topic`，可用 `--pub-start/--pub-end` 限定观察窗口 |
| 只要 JSON / 只要 HTML / 只要 Markdown | 用 `--output`（JSON）或 `--report-output`（HTML+MD），或 `render_report.py` 重渲染 |
| 连接 / 工具不存在 / 传参错误 | `mcp_client.py ping` / `list-tools` 排查；报脱敏后的缺失项 |

## Golden path for 资讯大数据报告

1. **解析匹配对象**：企业资讯工具（company_news / monitor）按企业名称直查；行业/主题/全文检索按关键词直查。含“公司/集团/有限/院/厂/中心/事务所/合作社/合伙”后缀时视为企业全称。
2. **调用资讯工具**：`information_company_news`（企业资讯明细）、`information_monitor`（view=statistics，情感分布与趋势）、`information_industry_news`（行业资讯）、`information_topic`（主题跟踪）。企业工具入参为 `matchKeyword`（企业全称）+ `keywordType`；检索类入参为 `matchKeyword`（关键词），可选 `pubDateBegin/pubDateEnd`。
3. **组装统一报告**：核心分析含企业资讯统计（KV）、舆情情感趋势（表）、企业资讯明细（表）、行业资讯（表）、资讯主题跟踪（表）。
4. **渲染三件套**：`compose_report.py --enterprise ... --output ... --report-output ...` 直接产出 JSON + HTML + Markdown；或 `render_report.py --input ... --output ...` 重渲染。
5. **返回路径**：返回 JSON、HTML、Markdown 文件路径，以及企业全称映射与数据口径（含情感过滤与发布区间）。

## 脚本速查

```bash
# 校验连接配置（脱敏）
python scripts/validate_config.py --allow-placeholders

# 连通性自测
python scripts/mcp_client.py ping
python scripts/mcp_client.py list-tools

# 干跑（不调真实 API，用样例数据组装报告骨架）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --dry-run \
  --output output/information.json \
  --report-output output/information.html

# 真实查询 + 渲染（企业资讯 + 统计 + 行业 + 主题）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --output output/information.json \
  --report-output output/information.html

# 按情感过滤企业资讯（仅负面）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" --sentiment 0 \
  --report-output output/info_negative.html

# 检索行业资讯（限定发布区间）
python scripts/compose_report.py \
  --enterprise "人工智能" \
  --pub-start 2025-01-01 --pub-end 2025-06-30 \
  --report-output output/info_industry.html

# 手动调单个工具
python scripts/mcp_client.py call-tool \
  --tool information_company_news \
  --arguments-json '{"matchKeyword": "示例科技有限公司", "keywordType": "name", "pageSize": 50}'

# 重渲染已有 JSON
python scripts/render_report.py --input output/information.json --output output/information.html
python scripts/render_report.py --input output/information.json --output output/information.md
```

## 输出字段

- `subject`：企业全称/关键词、匹配关键词、主体类型、解析说明（含发布区间、情感过滤、监控视图）。
- `abstract` / `summary`：封面摘要与详细摘要。
- `metrics`：企业资讯数、行业资讯数、主题资讯数、正面/负面/中性资讯数等指标卡。
- `caliber`：匹配对象、匹配方式（企业主体 vs 关键词；含情感与日期）、数据范围、产品、局限。
- `core_analysis`：企业资讯统计（KV）、舆情情感趋势（表）、企业资讯明细（表）、行业资讯（表）、资讯主题跟踪（表）。
- `representative_records`：代表性企业资讯记录（标题 / 来源 / 发布时间 / 情感）。
- `insights`：结构化解读（资讯曝光度 / 情感结构 / 行业语境）。
- `data_source`：MCP server、数据产品、生成时间、是否 dry-run。

若 API 调用失败，明确报出缺失的配置 / 缺失的工具 / MCP 错误 / 参数校验错误 / 上游网络错误，给出 dry-run 命令或配置步骤，绝不暴露密钥。
