# 人工逻辑红线验收清单

## 1. 验收前准备
- 本次验收请使用样例文件: `config/manual_risk_flags.yaml`
- 无需覆盖正式 manual_risk_flags.yaml/json；建议直接使用 `--manual-risk-file` 参数。
- 若你仍想手工替换正式文件，请先自行备份正式配置后再操作。
- 建议按顺序执行，避免并发运行导致缓存读写竞争。
- 建议执行顺序 1: `python -m src.main validate-manual-risk-flags --manual-risk-file config/manual_risk_flags.yaml --end-date 2025-12-31`
- 建议执行顺序 2: `python -m src.main suggest --manual-risk-file config/manual_risk_flags.yaml --end-date 2025-12-31`
- 建议执行顺序 3: `python -m src.main backtest --manual-risk-file config/manual_risk_flags.yaml --end-date 2025-12-31`

## 2. 案例 A 验收步骤：manual_pause_buy
- 当前样例文件中未找到对应案例。

## 3. 案例 B 验收步骤：manual_force_review
- 当前样例文件中未找到对应案例。

## 4. 案例 C 验收步骤：thesis_broken
- 当前样例文件中未找到对应案例。

## 5. 生效日期检查
- 人工检查同一标的在 effective_from 之前的建议与回测记录，应确认逻辑未生效。
- 人工检查 effective_from 当天或之后的建议与回测记录，应确认逻辑开始生效。
- 若发现生效日前后无差异，请优先核对 end-date、样例文件路径和报告中的 effective_from。

## 6. 合并逻辑检查
- 当价格红线与人工逻辑红线同时存在时，应以人工逻辑红线高优先级为准。
- 月报和回测报告中应能看到 final_reason_codes / final_human_readable_action 或对应中文动作说明。
- 若看到价格 YELLOW 与 manual_force_review 同时存在，最终动作应仍显示为“暂停新增，强制人工复核”或更高优先级动作。

## 7. 回归检查
- 改回默认正式文件后运行：`python -m src.main suggest --end-date 2025-12-31` 与 `python -m src.main backtest --end-date 2025-12-31`。
- 或者将样例文件中所有布尔值改回 false 后重新执行相同命令。
- 对比确认：新能力未悄悄改变原有未启用样例时的建议、回测与不自动卖出边界。

## 8. 重点查看的输出文件
- reports/manual/manual_risk_flags_validation.md
- reports/manual/manual_logic_risk_acceptance_report.md
- reports/monthly/monthly_report_*.md
- reports/backtest/backtest_report.md
