# 报告输出 — 资讯大数据报告

本文件规定 `information-report` skill 产出的报告结构、质量底线与渲染工作流。所有产物遵循 `AGENTS.md` 的统一 JSON 骨架与本 skill 的领域裁剪。

## 默认展示模式

- HTML：可分享 / 可交付的可视化报告；独立本地文件，内嵌 CSS，无调试 / 内部段落。
- Markdown：知识库 / wiki / PRD / 后续手工编辑。
- JSON：系统集成或二次处理。

`compose_report.py` 通过 `--report-output <path>` 同时产出 HTML + Markdown；`--output <path>` 产出 JSON。`render_report.py` 可基于已有 JSON 重渲染。

## 匹配语义

- **企业类工具**（`information_company_news` / `information_monitor`）：`--enterprise` 作为企业标识，配合 `--keyword-type`。
- **关键词类工具**（`information_industry_news` / `information_topic`）：`--enterprise` 作为行业/主题关键词直查。
- 可选过滤：`--sentiment 0|1|2|3`（企业资讯情感）、`--pub-start/--pub-end`（检索类发布区间）、`--view details|statistics`（监控视图，默认 statistics）。

## 报告结构（7 章）

1. **报告摘要**：分析对象、数据覆盖范围、核心发现、关键指标卡。
2. **查询对象与口径**：企业全称/关键词、匹配方式（企业主体 vs 关键词；含情感与日期）、数据范围、产品、局限。
3. **数据总览**：企业资讯数、行业资讯数、主题资讯数、正面/负面/中性资讯数等指标卡。
4. **核心分析**（资讯专属子章节，由 `core_analysis.sections` 驱动渲染）：
   - 企业资讯统计（KV：正面 / 负面 / 中性 / 未知 / 情感类别）。
   - 舆情情感趋势（表：周期/月份 / 负面 / 正面 / 中性）。
   - 企业资讯明细（表：标题 / 来源 / 发布时间 / 情感 / 简介）。
   - 行业资讯（表：标题 / 来源 / 发布时间 / 情感 / 简介）。
   - 资讯主题跟踪（表：标题 / 来源 / 发布时间 / 情感 / 简介）。
5. **代表性记录**：关键企业资讯记录 Top N（标题 / 来源 / 发布时间 / 情感）。
6. **特征与洞察**：结构化解读（资讯曝光度 / 情感结构 / 行业语境），每条含 `feature` / `evidence` / `interpretation`。
7. **数据口径与来源**：MCP server、数据产品、生成时间、是否 dry-run。

## 质量底线

- 报告脱离 Skill 上下文也可独立阅读；正文只见资讯事实与结构化数据。
- 绝不出现工具名、入参（如 `matchKeyword=...`、`sentimentLabel=...`）、product_id、内部字段名、空表、调试信息。
- HTML 采用研究报告视觉风格：A4 风、灰色顶部条纹、蓝色报告横幅、左侧目录 / 范围侧栏、深蓝章节标题、深蓝表头、浅蓝斑马行、打印友好分页。
- 数据为空时明确说明数据范围 / 口径，不渲染空表、不臆造事实。
- 绝不打印 `secret_id` / `secret_key` / 签名 / token / 原始签名请求。
- 报告口径中应说明本次所用的情感过滤与发布区间。

### 数据格式约束（铁律）

以下约束适用于 compose_report.py 组装数据与 render_report.py 渲染输出的全过程：

1. **嵌套 JSON 字符串必须解析**：MCP 返回的某些字段（如 `regCapital`、`addressValue`、`subscriptionDetail`）可能是 JSON 字符串（例：`{"coinType":"人民币","value":430000000.0}`）。compose 层必须调用 `_unwrap_json_str()` / `_parse_reg_capital()` / `_flatten_addr()` 解析为可读文本（如"4.30 亿 人民币"、"浙江省杭州市滨江区..."）。绝不在报告正文、表格单元格或指标值中输出原始 JSON 字符串。

2. **section 标题必须用中文**：`core_analysis.sections` 数组中每个 section 的 `title` 字段必须使用中文（如"企业基本信息"、"对外投资"、"股东信息"）。`key` 字段用英文 snake_case 供程序索引，但 `title` 绝不可显示英文 key。即使缺少 sections 数组，渲染器回退逻辑也内置了 `_TITLE_MAP` 映射。

3. **指标值可读化**：所有 `metrics` 的 `value` 字段必须格式化为人类可读形式：
   - 金额：`10995210218.0` → `109.95 亿 人民币`（≥1 亿用亿，≥1 万用万）
   - 地址：嵌套 dict → 省+市+区拼接 或取 `value` 字段
   - 比率：`0.8858` → `88.58%`
   - 日期：保持 `yyyy-MM-dd` 格式
   - "-" 表示字段缺失（MCP 未返回）；`0` 表示真实为零

4. **企业画像指标提取**：有 fuzzy_search 的 skill 必须从返回的 record 中提取 `regCapitalValue` / `foundTime` / `operStatus` / `enterpriseType` / `legalRepresentative`，通过 `_enrich_metrics_with_profile()` 追加为指标卡。

5. **分布派生指标**：`_derive_core_metrics()` 从 core_analysis 各 section 计算分布指标（CR3 集中度、覆盖城市/平台/类目数、价格区间、正面占比等），确保指标总数 M ≥ 6。

## 工作流

```bash
# 1. 干跑（不调真实 API，用样例数据组装报告骨架）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --dry-run \
  --output output/information.json \
  --report-output output/information.html

# 2. 真实查询 + 渲染
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --output output/information.json \
  --report-output output/information.html

# 3. 按情感过滤企业资讯（仅负面）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" --sentiment 0 \
  --report-output output/info_negative.html

# 4. 检索行业资讯（限定发布区间）
python scripts/compose_report.py \
  --enterprise "人工智能" \
  --pub-start 2025-01-01 --pub-end 2025-06-30 \
  --report-output output/info_industry.html

# 5. 重渲染已有 JSON
python scripts/render_report.py --input output/information.json --output output/information.html
python scripts/render_report.py --input output/information.json --output output/information.md
```

返回：JSON 路径、HTML 路径、Markdown 路径，以及企业全称映射与数据口径摘要。
