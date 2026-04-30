# 人工逻辑红线验收辅助报告

## 当前启用样例
- manual_risk_file: config/manual_risk_flags.yaml
- backtest_start_date: 2019-01-01
- check_end_date: 2025-12-31
- validation_valid: True

## 当前生效状态摘要
- end-date 前已生效的 symbol: 000333,000858,510300,510500,515180,518880,600036,600519,601318
- 强制人工复核的 symbol: 无
- thesis_broken 的 symbol: 无

## 最终动作预览
```text
symbol,asset_type,effective_from,active_on_end_date,effective_window_state,manual_pause_buy,manual_force_review,thesis_broken,final_pause_buy,final_force_review,final_priority_level,final_reason_codes,final_human_readable_action,expected_behavior,note,updated_at,updated_by,in_current_universe
000333,stock,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
000858,stock,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
510300,etf,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
510500,etf,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
515180,etf,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
518880,etf,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
600036,stock,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
600519,stock,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
601318,stock,1900-01-01,True,回测起点前已生效,False,False,False,False,False,6,green,正常,当前无人工逻辑动作,,2026-04-01,user,True
```

## 校验问题
当前无配置校验问题

## 每个案例的预期行为摘要
- 000333: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 000858: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 510300: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 510500: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 515180: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 518880: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 600036: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 600519: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作
- 601318: 正常 | 生效日期=1900-01-01 | 预期=当前无人工逻辑动作

## 说明
- 本报告仅用于验收人工逻辑红线链路，不构成投资建议。
- 这里的最终动作预览以价格侧 GREEN 作为基线，真正的价格红线与人工逻辑红线合并结果，请继续结合 suggest / backtest 报告核对。
- 使用 --manual-risk-file 可在不覆盖正式配置的前提下切换验收样例。
