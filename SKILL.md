---
name: information-report
description: Use for generating a professional information big-data report (资讯大数据报告) from the HandaaS information MCP — covering 企业资讯明细、企业资讯情感统计、行业资讯、资讯主题跟踪. Trigger when users ask for “资讯大数据报告”, “资讯分析报告”, “查一家公司的资讯”, “企业资讯监控”, “行业资讯”, “资讯主题跟踪”, “资讯检索”, or “企业舆情声量”. Infer the canonical enterprise name and topic keyword, pick the right MCP tools, and produce HTML + Markdown + JSON reports automatically. MCP 服务名称触发词：资讯热点跟踪。
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

## 内容整理与交付审校（强制）

1. **口径先分层**：企业资讯、独立全文检索、主题跟踪是不同产品与查询范围，记录数只能并列披露，不能相加、相除或互相替代；主题跟踪与全文检索同源复用时须说明。
2. **情感是上游标签**：正面/负面/中性/未知由模型给出，未逐条人工核验；不得由标题或标签推断声誉、经营影响或因果关系，不得输出无证据的应对建议。
3. **样本与全量分开**：企业资讯明细只代表当前页；关联共现实体、媒体来源、状态分布均写“样本内/最多展示 N 个”。主体自身仅按全/半角括号与空白差异排除，不得把主体算作关联企业；其他实体名称不得因标点或近似而合并。
4. **转载与事件分开**：仅标题完全一致的记录可标“疑似重复”；近义标题、改标题转载、同一事件多篇进展不自动合并，保留原列表供核对。
5. **趋势只比完整月份**：当前月为不完整月份，不参与环比；近两月任一 <5 条或最新数据距报告期超过 2 个月时，不写“近月升降”。枚举值（如 `enterprise`、`positive`）必须转为中文；未知值保留原文并标注。
6. 原始标题、来源、时间、链接、标签保留；正常生成与离线修订均调用 `apply_content_review(report)`，不新增查询。

### 草稿 → AI 审校 → 最终交付

1. **采集一次，只出草稿**：本 Skill 的采集脚本（`compose_report.py` 或 `compose_fusion_report.py`，以脚本速查为准）在正常生成和 `--dry-run` 时都于写盘前标记 `data_source.semantic_review.status=pending`，产出 `output/draft.json` 与 `output/draft.html`/`draft.md`。后两者只是预览，不能交付；`apply_content_review`、`organize_report` 等确定性整理不等于实际 AI 审校。
2. **实际阅读再判断**：当前 AI 智能体打开 draft，逐项阅读 `subject`、`core_analysis`、`metrics`、`caliber`、`analysis_request`、`data_source`，按含义做标准化归类、3–5 句三层摘要和有证据的洞察；只引用本报告实际存在的 JSON Pointer，数字逐字取自所引 values，保留否定、最高/至少/至多、试用期/转正后、仅限/部分、疑似/待定/已失效等限定；无数据不生成事实或业务判断。
3. **准备审校请求**：`python scripts/review_report.py --input output/draft.json --request output/review-request.json`。该命令只读草稿，不调用 MCP、外部模型 API，也不新增查询。
4. **写回实际判断**：按请求的 `response_fields` 将逐句摘要、标准化和含 evidence 的洞察写入 `output/ai-review.json`；`source_sha256` 必须与请求一致。字段与 JSON Pointer 规则见 `references/report-output.md`。
5. **应用并核对成品**：`python scripts/review_report.py --input output/draft.json --review output/ai-review.json --output output/final/report.json --report-output output/final/report.html`；核对最终 JSON、HTML、Markdown（目录、图表、空章节）后才交付。不得停在审校请求文件，也不得另存手工润色件冒充最终报告。
6. **展示纪律**：空板块连标题和目录一起隐藏；真实 `0`/`False` 原样保留；失败或未查询只在口径限制中简述，不补 0、不推断“无风险”或“无数据”。空维度只影响展示，不从 `quality_report` 分母抹去未覆盖维度；AI 标准化/摘要是解释视图，不新增数据来源或源数据覆盖率。

## MCP 服务入口

- MCP 服务当前名称：资讯热点跟踪（连接仍使用原服务目录标识）。

- 上游 MCP 项目：`handaas-mcp-server/information-mcp-server`（位于 `HANDAAS_MCP_SERVER_ROOT` 或本仓库同级目录）。
- Remote MCP：设置环境变量 `INFORMATION_MCP_URL`（streamable-http），可选 `INFORMATION_MCP_TOKEN`。
- 本地 MCP：设置 `HANDAAS_MCP_SERVER_ROOT` 指向 `handaas-mcp-server` 仓库根目录；该 server 自己的 `.env` 提供 `INTEGRATOR_ID` / `SECRET_ID` / `SECRET_KEY`。
- 首次真实查询前，运行 `scripts/mcp_client.py ping` 与 `scripts/mcp_client.py list-tools` 验证连通。

## 按需加载 references

- 不清楚该 MCP 有哪些工具、参数、返回字段、何时调用：`references/mcp-tools-reference.md`。
- 报告结构、章节、质量底线、渲染工作流：`references/report-output.md`。

## 付费调用与预算约束（必读）

1. 每次业务工具调用与每次明细翻页都可能计费；想要 total/页数只是为了精确规划，不构成默认全量拉取的授权。
2. 调用前先推演所需结论与数据维度，确定工具/参数计划、必要页数与最大调用预算。total 未知时，第一个必要明细页既是数据又是 total 探测，绝不为此重复付费。
3. 优先用统计/画像/聚合接口（如 `information_monitor` statistics 视图）回答问题；只在结论、图表、代表记录或明确全量/计数需求确实需要时取明细。只有确实要求综合报告时才跑完整流水线，绝不因为工具存在就全部调用相关维度。
4. 用 schema 允许的最大合理 pageSize 取所需行数，证据/样本目标满足即停，且不超过明确预算。更多调用必须有具体缺失结论支撑，不因为"补齐所有章节"而追加；不得用样本分布冒充全量结论。预算不足以支撑关键结论时，先说明证据缺口与预计额外调用数，等明确授权后再扩大——不得静默降级结论，也不得静默扩大计费范围。
5. 当前任务/报告内复用相同请求（含第一页规划数据）：同一 tool+相同参数只调用一次；不要为渲染重跑 compose/MCP——用已保存 JSON 本地重渲染；不得自动重试、重复取统计/明细或并行获取相同数据；补充查询先列明缺口并复用已返回记录。
6. `total_pages`/`remaining_pages` 是按请求 pageSize 的估算；短但非空的页仍有剩余记录时在预算内继续。只有稳定有效 total 与实际扫描数一致才算完整采集；报错、提前空页、重复页、total 变更/缺失、数量溢出均为不完整。显式预算或样本目标停止即部分采集，绝不宣称全量。不调用无关或不必要维度的工具。

本 skill 分页明细接口：`information_company_news` / `information_search` / `information_topic`（pageSize≤50），预算经 `--max-pages`（默认 1）传递；`information_monitor`（statistics 视图）与无分页场景为单次调用，不进入分页预算。`information_search` 与 `information_topic` 复用同一上游产品且参数一致，同参时直接复用已付费数据，不重复计费。

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

- **渲染前置检查**：执行会产出含图表 HTML / PDF 的报告命令前，先验证 `node --version` 与本 skill 自带 `assets/vendor/echarts.min.js` 存在；内嵌静态 SVG 的生成需要 Node.js（推荐当前 LTS，无需 npm 包），缺失时报告生成明确报错。查看已生成的 HTML 与 Markdown 输出不需要 Node。

## 脚本速查
以下采集示例只生成待审校草稿（`data_source.semantic_review.status=pending`）；最终报告须按上方门禁用 `review_report.py` 生成。

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
  --max-pages 1 \
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
