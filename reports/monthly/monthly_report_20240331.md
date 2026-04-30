# 月度定投建议报告 - 2024-03-31

## 数据来源
- 数据模式: demo
- 数据提供方: demo
- 历史接口: n/a
- 复权模式: demo
- 最近一次数据更新时间: 2026-03-31 19:34:50
- 最新数据日期: 2024-03-29
- 当前命中的交易日: 2024-03-31

## 本月预算
- 总预算: 10000.00
- ETF 预算: 8000.00
- 股票预算: 2000.00

## 配置摘要
- monthly_budget: 10000.0
- etf_total_weight: 0.8
- stock_total_weight: 0.2
- adjustment_mode: forward
- min_trade_lot: 100
- monthly_rule: first_trading_day
- weekly_rule: last_trading_day_of_week

## 人工复核事项
- 510300: 相对参考高点回撤 44.53%，超过 RED 阈值
- 510500: 相对参考高点回撤 41.34%，超过 RED 阈值
- 518880: 相对参考高点回撤 53.57%，超过 RED 阈值

## 当前持仓与目标
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

## 风险状态
```text
symbol,asset_type,status,reasons,pause_buy,manual_review,metric_value
510300,etf,RED,相对参考高点回撤 44.53%，超过 RED 阈值,True,True,0.4453098931789168
510500,etf,RED,相对参考高点回撤 41.34%，超过 RED 阈值,True,True,0.4134213943226878
515180,etf,GREEN,ETF 风险状态正常,False,False,0.02762372437783611
518880,etf,RED,相对参考高点回撤 53.57%，超过 RED 阈值,True,True,0.5357117220630513
600519,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,
000858,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,
600036,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,
000333,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,
601318,stock,GREEN,尚无持仓成本，允许按计划定投,False,False,
```

## 风险状态汇总
```text
status,count
GREEN,6
RED,3
```

## 暂停买入标的
```text
symbol,status,reasons
510300,RED,相对参考高点回撤 44.53%，超过 RED 阈值
510500,RED,相对参考高点回撤 41.34%，超过 RED 阈值
518880,RED,相对参考高点回撤 53.57%，超过 RED 阈值
```

## 数据质量摘要
```text
symbol,asset_type,rows,start_date,end_date,duplicate_dates,missing_required_rows,raw_columns,standardized_columns,note
510300,etf,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
510500,etf,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
515180,etf,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
518880,etf,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
600519,stock,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
000858,stock,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
600036,stock,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
000333,stock,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
601318,stock,1369,2019-01-01,2024-03-29,0,0,,"date,symbol,asset_type,open,high,low,close,volume,amount",synthetic_data
```

## 未成交说明
当前报告为建议模式，未实际执行成交；若当日无行情或触发风险暂停，将在回测/执行阶段记录为未成交。

## 说明
- 本建议仅用于人工确认，不接自动下单。
- YELLOW/RED 标的默认暂停新增买入。
- 当前版本不自动卖出，卖出仅保留人工复核接口。