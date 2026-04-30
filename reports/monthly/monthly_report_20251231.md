# 月度定投建议报告 - 2025-12-31

## 数据模式与来源
- 数据模式: real
- 数据提供方: efinance
- 历史接口: stock.get_quote_history
- 当前复权模式: forward
- 最新数据日期: 2025-12-31
- 最近更新时间: 2026-04-01 16:22:51
- 本月实际命中的交易日: 2025-12-31

## 当前配置参数摘要
- monthly_budget: 10000.0
- etf_total_weight: 0.8
- stock_total_weight: 0.2
- adjustment_mode: forward
- min_trade_lot: 100
- monthly_rule: first_trading_day
- weekly_rule: last_trading_day_of_week

## 当前组合快照
- total_asset_estimate: 0.0
- holdings_market_value: 0.0
- recorded_cash: 0.0
```text
asset_type,market_value,actual_ratio
etf,0.0,0.0
stock,0.0,0.0
```

## 当前持仓与目标权重
```text
symbol,name,asset_type,category,target_weight,quantity,avg_cost,last_price,market_value,current_weight,weight_gap
510300,沪深300ETF,etf,broad_index,0.3,0,0.0,0.0,0.0,0.0,0.3
510500,中证500ETF,etf,broad_index,0.2,0,0.0,0.0,0.0,0.0,0.2
515180,红利ETF,etf,dividend,0.2,0,0.0,0.0,0.0,0.0,0.2
518880,黄金ETF,etf,defensive,0.1,0,0.0,0.0,0.0,0.0,0.1
000333,美的集团,stock,,0.04,0,0.0,0.0,0.0,0.0,0.04
000858,五粮液,stock,,0.04,0,0.0,0.0,0.0,0.0,0.04
600036,招商银行,stock,,0.04,0,0.0,0.0,0.0,0.0,0.04
600519,贵州茅台,stock,,0.04,0,0.0,0.0,0.0,0.0,0.04
601318,中国平安,stock,,0.04,0,0.0,0.0,0.0,0.0,0.04
```

## 本月建议买入
```text
symbol,asset_type,target_weight,current_weight,recommended_amount,status,pause_buy,manual_review,reasons,manual_pause_buy,manual_force_review,thesis_broken,final_priority_level,final_reason_codes,final_human_readable_action,logic_note
510300,etf,0.3,0.0,4000.0,GREEN,False,False,ETF 风险状态正常,False,False,False,6,green,正常,
510500,etf,0.2,0.0,2666.666666666667,GREEN,False,False,ETF 风险状态正常,False,False,False,6,green,正常,
515180,etf,0.2,0.0,0.0,RED,True,True,人工标记 manual_force_review=true；相对参考高点回撤 4.72%，进入 YELLOW 区域；跌破长期均线且持续弱势,False,True,False,2,"manual_force_review,price_yellow",暂停新增，强制人工复核,用于验收强制复核逻辑，并观察与价格红线合并后的最终动作
518880,etf,0.1,0.0,1333.3333333333335,GREEN,False,False,ETF 风险状态正常,False,False,False,6,green,正常,
600519,stock,0.04,0.0,0.0,YELLOW,True,False,人工标记 manual_pause_buy=true；尚无持仓成本，允许按计划定投,True,False,False,3,manual_pause_buy,暂停新增，等待人工解除,用于验收暂停新增逻辑
000858,stock,0.04,0.0,0.0,RED,True,True,人工标记 thesis_broken=true；尚无持仓成本，允许按计划定投,False,False,True,1,thesis_broken,停止新增，最高优先级人工处理,用于验收逻辑失效处理；故意不额外打开 manual_force_review，以验证 thesis_broken 可独立生效
600036,stock,0.04,0.0,666.6666666666667,GREEN,False,False,尚无持仓成本，允许按计划定投,False,False,False,6,green,正常,
000333,stock,0.04,0.0,666.6666666666667,GREEN,False,False,尚无持仓成本，允许按计划定投,False,False,False,6,green,正常,
601318,stock,0.04,0.0,666.6666666666667,GREEN,False,False,尚无持仓成本，允许按计划定投,False,False,False,6,green,正常,
```

## 本月暂缓或无法执行项目
```text
symbol,asset_type,recommended_amount,status,blocked_reason,reasons
510300,etf,4000.0,GREEN,缺少可用价格,ETF 风险状态正常
510500,etf,2666.666666666667,GREEN,缺少可用价格,ETF 风险状态正常
515180,etf,0.0,RED,缺少可用价格,人工标记 manual_force_review=true；相对参考高点回撤 4.72%，进入 YELLOW 区域；跌破长期均线且持续弱势
518880,etf,1333.3333333333335,GREEN,缺少可用价格,ETF 风险状态正常
600519,stock,0.0,YELLOW,缺少可用价格,人工标记 manual_pause_buy=true；尚无持仓成本，允许按计划定投
000858,stock,0.0,RED,缺少可用价格,人工标记 thesis_broken=true；尚无持仓成本，允许按计划定投
600036,stock,666.6666666666667,GREEN,缺少可用价格,尚无持仓成本，允许按计划定投
000333,stock,666.6666666666667,GREEN,缺少可用价格,尚无持仓成本，允许按计划定投
601318,stock,666.6666666666667,GREEN,缺少可用价格,尚无持仓成本，允许按计划定投
```

## 当前风险灯号总览
```text
status,count
GREEN,6
RED,2
YELLOW,1
```

## 人工逻辑红线摘要
```text
symbol,asset_type,manual_pause_buy,manual_force_review,thesis_broken,final_human_readable_action,logic_note,effective_from
515180,etf,False,True,False,暂停新增，强制人工复核,用于验收强制复核逻辑，并观察与价格红线合并后的最终动作,2025-06-01
600519,stock,True,False,False,暂停新增，等待人工解除,用于验收暂停新增逻辑,2025-01-01
000858,stock,False,False,True,停止新增，最高优先级人工处理,用于验收逻辑失效处理；故意不额外打开 manual_force_review，以验证 thesis_broken 可独立生效,2025-03-01
```

## 风险明细
```text
symbol,asset_type,status,reasons,pause_buy,manual_review,metric_value,price_status,price_reasons,manual_pause_buy,manual_force_review,thesis_broken,logic_reasons,final_pause_buy,final_force_review,final_priority_level,final_reason_codes,final_human_readable_action,logic_note,effective_from,updated_at,updated_by
510300,etf,GREEN,ETF 风险状态正常,False,False,0.14068299925760952,GREEN,ETF 风险状态正常,False,False,False,,False,False,6,green,正常,,,,
510500,etf,GREEN,ETF 风险状态正常,False,False,0.008040068538289171,GREEN,ETF 风险状态正常,False,False,False,,False,False,6,green,正常,,,,
515180,etf,RED,人工标记 manual_force_review=true；相对参考高点回撤 4.72%，进入 YELLOW 区域；跌破长期均线且持续弱势,True,True,0.04722222222222211,YELLOW,相对参考高点回撤 4.72%，进入 YELLOW 区域；跌破长期均线且持续弱势,False,True,False,人工标记 manual_force_review=true,True,True,2,"manual_force_review,price_yellow",暂停新增，强制人工复核,用于验收强制复核逻辑，并观察与价格红线合并后的最终动作,2025-06-01,2026-04-01,acceptance_sample
518880,etf,GREEN,ETF 风险状态正常,False,False,0.03616580310880831,GREEN,ETF 风险状态正常,False,False,False,,False,False,6,green,正常,,,,
600519,stock,YELLOW,人工标记 manual_pause_buy=true；尚无持仓成本，允许按计划定投,True,False,,GREEN,尚无持仓成本，允许按计划定投,True,False,False,人工标记 manual_pause_buy=true,True,False,3,manual_pause_buy,暂停新增，等待人工解除,用于验收暂停新增逻辑,2025-01-01,2026-04-01,acceptance_sample
000858,stock,RED,人工标记 thesis_broken=true；尚无持仓成本，允许按计划定投,True,True,,GREEN,尚无持仓成本，允许按计划定投,False,False,True,人工标记 thesis_broken=true,True,True,1,thesis_broken,停止新增，最高优先级人工处理,用于验收逻辑失效处理；故意不额外打开 manual_force_review，以验证 thesis_broken 可独立生效,2025-03-01,2026-04-01,acceptance_sample
600036,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,,GREEN,尚无持仓成本，允许按计划定投,False,False,False,,False,False,6,green,正常,,,,
000333,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,,GREEN,尚无持仓成本，允许按计划定投,False,False,False,,False,False,6,green,正常,,,,
601318,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,,GREEN,尚无持仓成本，允许按计划定投,False,False,False,,False,False,6,green,正常,,,,
```

## 下期优先定投标的建议
```text
symbol,asset_type,target_weight,current_weight,recommended_amount,status,pause_buy,manual_review,reasons,manual_pause_buy,manual_force_review,thesis_broken,final_priority_level,final_reason_codes,final_human_readable_action,logic_note
510300,etf,0.3,0.0,4000.0,GREEN,False,False,ETF 风险状态正常,False,False,False,6,green,正常,
510500,etf,0.2,0.0,2666.666666666667,GREEN,False,False,ETF 风险状态正常,False,False,False,6,green,正常,
518880,etf,0.1,0.0,1333.3333333333335,GREEN,False,False,ETF 风险状态正常,False,False,False,6,green,正常,
600036,stock,0.04,0.0,666.6666666666667,GREEN,False,False,尚无持仓成本，允许按计划定投,False,False,False,6,green,正常,
000333,stock,0.04,0.0,666.6666666666667,GREEN,False,False,尚无持仓成本，允许按计划定投,False,False,False,6,green,正常,
```

## 数据质量摘要
```text
symbol,asset_type,rows,start_date,end_date,duplicate_dates,missing_required_rows,fallback_used,cache_hit,latest_update
510300,etf,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
510500,etf,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
515180,etf,1463,2019-12-20,2025-12-31,0,0,False,True,2026-04-01 16:22:51
518880,etf,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
600519,stock,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
000858,stock,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
600036,stock,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
000333,stock,1688,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
601318,stock,1699,2019-01-02,2025-12-31,0,0,False,True,2026-04-01 16:22:51
```

## 本月需要人工判断的事项清单
- 515180: 暂停新增，强制人工复核 | 原因: 人工标记 manual_force_review=true；相对参考高点回撤 4.72%，进入 YELLOW 区域；跌破长期均线且持续弱势
- 000858: 停止新增，最高优先级人工处理 | 原因: 人工标记 thesis_broken=true；尚无持仓成本，允许按计划定投

## 重要限制说明
- 本报告为建议模式输出，不自动下单。
- YELLOW / RED 默认暂停新增买入，不自动卖出。
- 当前总资产估算包含持仓市值与已记录现金，不代表账户实时净值。
- 本建议仅用于人工确认，不接自动下单。
- 人工逻辑红线与价格红线会统一合并，暂停新增优先于正常定投。
- 当前版本不自动卖出，卖出仍需人工复核后执行。