# 中国会计准则财务技能包

基于中国《小企业会计准则》(财会[2011]17号)、《企业会计准则》(财会[2006]3号及后续修订)、中国注册会计师审计准则(CAS) 构建的 AI Agent 技能包。

**覆盖小企业（年收入<500万）→ 成长企业（500-3000万）→ 中型企业（3000万+） 全规模段。**

覆盖**准则选择 → 记账理账 → 报表生成 → 税务计算 → 审计程序** 的完整财务工作流。

## 安装

```bash
npx skills add openaccountant/skills  # 待发布
```

或直接复制到 skills 目录：

```bash
cp -r china-accounting/* ~/.claude/skills/
```

## Skills 清单

### 💼 记账理账 (business/) — 11 skills

| Skill | 功能 | 覆盖 |
|---|---|---|
| `accounting-framework` | 准则选择指南 — 根据收入/规模/行业自动判断使用哪套准则 | 全规模 |
| `chart-of-accounts` | 标准科目表 — 小企业66科目 + 企业准则167科目，含编码和借贷方向 | 全规模 |
| `journal-entry` | 记账凭证编制 — 标准格式，借贷平衡验证 | 全规模 |
| `profit-loss` | 利润表 — 小企业简化版 + 企业准则完整版（含公允价值变动、减值损失等） | 全规模 |
| `balance-sheet` | 资产负债表 — 两套准则格式 + 递延税/商誉/使用权资产等 | 全规模 |
| `cash-flow` | 现金流量表 — 经营/投资/筹资活动现金流 | 全规模 |
| `gross-net-margin` | 毛利率/净利率分析 — 驱动因素拆解 + 行业对标 + 利润质量分析 | 全规模 |
| `vat-accounting` | 增值税会计处理 — 小规模/一般纳税人，数电发票 | 全规模 |
| `income-tax` | 企业所得税 — 应付税款法(小企业) + 资产负债表债务法(企业准则递延税) | 全规模 |
| `individual-tax` | 个人所得税 — 经营所得/综合所得、专项附加扣除 | 全规模 |
| `month-end-close` | 月末结账 — 5步(小企业) → 7步(企业准则含减值+递延税+公允价值) | 全规模 |

### 🔍 审计 (audit/)

| Skill | 功能 |
|---|---|
| `audit-master` | 审计总控 — 项目管理和工作流编排 |
| `risk-assessment` | 风险评估 — CAS 1211，了解被审计单位、识别重大错报风险 |
| `materiality` | 重要性水平计算 — CAS 1221，整体/实际执行/微小临界值 |
| `cash-audit` | 货币资金实质性程序 — 银行函证、现金盘点、余额调节表 |
| `receivables-audit` | 应收账款实质性程序 — 函证、账龄分析、坏账准备测试 |
| `inventory-audit` | 存货实质性程序 — 监盘、计价测试、截止测试 |
| `fixed-assets-audit` | 固定资产实质性程序 — 实地检查、折旧重新计算 |
| `payables-audit` | 应付账款实质性程序 — 函证、截止测试（完整性导向） |
| `revenue-audit` | 收入实质性程序 — 特殊风险、分析程序、截止测试 |
| `expenses-audit` | 费用实质性程序 — 分析程序、抽凭测试、完整性检查 |
| `audit-adjustments` | 审计调整分录 — 重分类/账项/跨年滚调 |
| `audit-report` | 审计报告 — CAS 1501/1502/1503，四种意见类型 |

### 📋 参考资料 (shared/)

| Skill | 功能 |
|---|---|
| `coa-reference` | 小企业会计准则科目表完整参考 |
| `tax-rates-reference` | 2025-2026 税率速查表（增值税/企税/个税/附加税/印花税） |

## 平台兼容

| 平台 | 路径 |
|---|---|
| Claude Code | `.claude/skills/` |
| Cursor | `.cursor/skills/` |
| OpenCode | `.opencode/skills/` |
| Trae (中国版) | `.trae-cn/skills/` |

## 免责声明

本技能包提供的信息仅供参考和学习用途。所有财务处理、税务申报和审计意见应由持证会计师（CPA）或税务师审核确认。因使用本技能包信息产生的任何后果由使用者自行承担。

## 附：自用量化系统

同仓库 [`quant/`](quant/README.md) 是一套用开源库拼起来的个人量化流水线（数据湖、策略、回测、模拟盘、看板），和会计准则技能包相互独立。

## License

MIT
