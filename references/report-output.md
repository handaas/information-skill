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

5. **分布派生指标**：来源数、关联实体数只来自当前明细样本；“舆情监控周期”不是业务指标，已移除；compose 不追加这类样本指标。

## 内容审校清单（交付前逐项核对）

1. 企业资讯 / 全文检索 / 主题跟踪三套数量不得相加或相除；同源复用要说明。
2. 情感标签是模型输出，未人工核验；不得由标题/标签推断声誉、责任或经营影响。
3. 仅按全/半角括号与空白差异排除主体自身；其他实体名称保留原值，不因标点、别名或近似字符串合并。最多展示 15 个时不得说成“共 15 个”。
4. 枚举值转中文（`enterprise`→企业、`positive`→正面）；未知值保留原文并标注“未知”。
5. 当前月为不完整月份；近两月任一 <5 条或最新数据超过 2 个月未更新，不作“近月”趋势判断。
6. 标题、来源、时间、链接、原文标签保留；仅标题完全一致的重复可标注，近义标题需人工复核。

## AI 审校交付门禁（草稿 → final）

`compose_*` 正常生成与 `--dry-run` 只产出草稿：JSON 标记 `data_source.semantic_review.status=pending`，同名 HTML/Markdown 带“数据草稿（待AI语义审校）”提示，不能交付。`apply_content_review`/`organize_report` 是确定性整理，不是 AI 审校。

```bash
python scripts/review_report.py --input output/draft.json --request output/review-request.json
# 当前 AI 阅读请求中的 report 后写 output/ai-review.json
python scripts/review_report.py --input output/draft.json --review output/ai-review.json \
  --output output/final/report.json --report-output output/final/report.html
```

请求含 `source_sha256`、`report`、`visible_section_keys`、`instructions`、`response_fields`；响应：

```json
{
  "source_sha256": "<与请求一致>",
  "summary": [{"text": "逐句摘要", "sources": ["/core_analysis/..."], "kind": "fact"}],
  "normalizations": [{"sources": ["/core_analysis/..."], "category": "类别", "normalized": "规范表达", "evidence": "原文摘录", "reason": "理由"}],
  "insights": [{"feature": "特征", "evidence": "证据摘录", "interpretation": "解读", "sources": ["/metrics/0"]}]
}
```

- `source_sha256` 必须与请求一致；不一致须重新请求，不能沿用旧判断。
- `sources` 使用 JSON Pointer，只能指向本报告实际存在的 `/subject/…`、`/core_analysis/…`、`/metrics/…`、`/caliber/…`、`/data_source/…`、`/analysis_request/…`；`/core_analysis/sections`、`/data_source/semantic_review` 与旧 `abstract`/`summary`/`insights` 不是事实依据。
- 每项至少一个来源且不能重复路径；同一来源可支持多项判断；不能借其他企业、案例、记录或常识补本记录。
- `summary` 写 3–5 句有信息量的逐句摘要，`kind` 只能是 `fact`/`interpretation`/`limitation`；无数据依据只能写 `limitation`。`normalizations` 是独立视图，原文不改写；`evidence` 必填，由当前 AI 选择简洁可读的原文摘录作为“原文依据”列，并由同项 `sources` 支撑，完整原值仍保留在 draft/request 与来源 SHA 记录中；必须保留否定、最高、至少、至多、试用期、转正后、仅限、部分、疑似、待定、已失效等限定；不同主体、互斥金额或比例不能合并；没有实际归类需要时可为空；`insights` 的 `feature`、`evidence`、`interpretation` 都须由同一 `sources` 支撑；`evidence` 是实际 AI 写的简洁可读证据摘录，保留来源数字、单位与限定。
- 所有文本（含 `normalized`、`category`、`reason`、`evidence`、洞察）中的数字必须逐字出现在所引 values 中，不新造派生数字、不改精度；需要派生指标先在脚本计算再引用。
- 只使用本次数据，不调用 MCP/外部模型 API/新增查询。应用后 `status=reviewed` 并记录来源 SHA-256、原 `generated_at`、审校时间与判断证据；原查询时间和原件不变。`summary` 写入 `abstract`/`summary`/`executive_summary`，`normalizations` 写入 `core_analysis.ai_normalization`（独立表格），`insights` 写入 `insights`；原始字段不改写。

**展示与交付**：空板块连标题和目录一起隐藏，但只能影响展示，不能从 `quality_report` 分母抹去未覆盖维度或提高覆盖率；真实 `0`/`False` 保留，缺失/未查询不等于 0；失败只写口径限制，不推断“无风险”。AI 标准化/摘要是解释视图，不新增数据来源或覆盖率。核对最终 JSON/HTML/Markdown 后才交付；请求文件、草稿或手工润色件不算完成。

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

审校复核：完整保留有来源的摘要句子及采集层“数据缺口／主体解析受阻”提示；重审不得引用 `/core_analysis/ai_normalization` 等既有 AI 视图作为原始证据。HTML 与 Markdown 应使用一致的样本数量、趋势顺序及数据列，单元格中的竖线和换行不得破坏表格结构。
