# 默认参数建议说明

## 1. 目的说明
- 本报告用于把敏感性测试数字转成保守、可执行的默认参数建议，不以“收益最高”作为唯一标准。

## 2. 当前默认参数组摘要
- baseline group: baseline
- adjustment_mode: forward
- monthly_buy_rule: first_trading_day
- ETF redline: 15.00% / 25.00%
- STOCK redline: 12.00% / 20.00%

## 3. 每个默认参数的保留/调整建议
- adjustment_mode: 保留，但需备注限制 | 建议值: forward | 理由: 当前 `adj_none` 未成功完成，证据不足以支持更换默认复权模式；应继续保留 forward，并在报告中注明 none 模式证据不完整。
- monthly_buy_rule: 保留 | 建议值: first_trading_day | 理由: 月末买入在当前样本下收益略弱、回撤略高，说明每月第 1 个交易日更贴近 baseline 的平衡表现。
- etf_redline: 保留 | 建议值: YELLOW=0.15, RED=0.25 | 理由: ETF 红线收紧会明显增加现金拖累与 RED 触发，放宽则会降低触发但抬升回撤；15% / 25% 更符合长期定投且不轻易卖出的定位。
- stock_redline: 证据不足，暂不调整 | 建议值: YELLOW=0.12, RED=0.20 | 理由: 当前测试几乎未观察到股票红线变动对结果的影响，更像样本证据不足；在股票仅占 20% 且当前仓位利用有限的前提下，暂不建议主动改动默认值。
- baseline_default: 建议保留但需备注限制 | 建议值: baseline | 理由: baseline 当前更像可执行的中性默认配置：ETF 红线与月初执行日有明确支撑，但复权模式与股票红线仍存在证据不完整的备注项。

## 4. 推荐结论总表
```text
parameter,tag,recommended_value
adjustment_mode,保留，但需备注限制,forward
monthly_buy_rule,保留,first_trading_day
etf_redline,保留,"YELLOW=0.15, RED=0.25"
stock_redline,证据不足，暂不调整,"YELLOW=0.12, RED=0.20"
baseline_default,建议保留但需备注限制,baseline
```

## 5. 建议理由
- adjustment_mode: 当前 `adj_none` 未成功完成，证据不足以支持更换默认复权模式；应继续保留 forward，并在报告中注明 none 模式证据不完整。
- monthly_buy_rule: 月末买入在当前样本下收益略弱、回撤略高，说明每月第 1 个交易日更贴近 baseline 的平衡表现。
- etf_redline: ETF 红线收紧会明显增加现金拖累与 RED 触发，放宽则会降低触发但抬升回撤；15% / 25% 更符合长期定投且不轻易卖出的定位。
- stock_redline: 当前测试几乎未观察到股票红线变动对结果的影响，更像样本证据不足；在股票仅占 20% 且当前仓位利用有限的前提下，暂不建议主动改动默认值。
- baseline_default: baseline 当前更像可执行的中性默认配置：ETF 红线与月初执行日有明确支撑，但复权模式与股票红线仍存在证据不完整的备注项。

## 6. 限制说明
- 当前结论依赖已有 sensitivity-test 结果，若输入文件缺失或样本更新，应重新生成。
- 当前结果仍受真实数据可用性、历史起点差异、MVP 级市场摩擦建模影响。
- 当前系统仍未启用自动卖出，红线主要用于提醒、暂停新增与人工复核。
