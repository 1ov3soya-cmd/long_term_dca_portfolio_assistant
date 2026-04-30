# 稳健性结论摘要

## 1. 本轮目标说明
- 本轮结论基于已有 sensitivity-test 结果生成，目标是判断默认参数是否相对稳健，而不是寻找最优参数。
- 当前系统定位仍是长期定投、资产配置、风险提醒与人工确认执行工具，不等于自动交易系统。

## 2. Baseline 配置摘要
- group_name: baseline
- data_mode: real
- provider: efinance
- source_api: stock.get_quote_history
- backtest_range: 2019-01-01 -> 2025-12-31
- adjustment_mode: forward
- monthly_buy_rule: first_trading_day
- ETF redline: 15.00% / 25.00%
- STOCK redline: 12.00% / 20.00%

## 3. 测试成功/失败概览
- 成功组数量: 7
- 失败组数量: 1
- 失败组: adj_none | 原因: eFinance 获取历史行情失败: symbol=510300, asset_type=etf, error=HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf11%2Cf12%2Cf13&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&beg=20190101&end=20251231&rtntype=6&secid=1.510300&klt=101&fqt=0 (Caused by ProxyError('Unable to connect to proxy', NewConnectionError("HTTPSConnection(host='127.0.0.1', port=9): Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。")))

## 4. 参数敏感度结论
- annualized_return: 最敏感参数为 ETF 红线（来自 etf_redline_tighter，影响=-0.005056）
- max_drawdown: 最敏感参数为 ETF 红线（来自 etf_redline_tighter，影响=-0.010688）
- invested_ratio: 最敏感参数为 ETF 红线（来自 etf_redline_tighter，影响=-0.054998）
- cash_drag: 最敏感参数为 ETF 红线（来自 etf_redline_tighter，影响=46198.580180）
- unfilled_amount: 最敏感参数为 ETF 红线（来自 etf_redline_tighter，影响=816.070461）
- total_red_triggers: 最敏感参数为 ETF 红线（来自 etf_redline_looser，影响=-100.000000）

## 5. 高敏感参数 vs 稳健参数
- 高敏感参数: ETF 红线(2.19)
- 中等敏感参数: 无
- 相对稳健参数: 月度定投执行日(0.22), 滑点(0.01), 股票红线(0.00)

## 6. 关键风险提示
- 复权模式: 本轮 `adj_none` 失败，当前证据不足以否定 forward 默认值，同时提示复权模式切换仍受真实数据可用性影响。
- ETF 红线方向性: ETF 红线更紧时，现金拖累与 RED 触发通常上升，回撤可能下降；更松时，触发次数下降、资金利用率略改善，但回撤更容易抬升。15% / 25% 更像中性折中。
- 股票红线方向性: 当前样本下，股票红线收紧或放宽几乎没有改变量化结果，更像当前样本证据不足，而不是股票红线永远不重要。
- 月度定投执行日: 月末买入在当前样本下年化收益略低、回撤略高，但 RED 触发更少，说明执行日会改变路径表现，不过影响量级中等。
- 滑点敏感性: 轻量上调滑点后，各项结果变化很小，说明这组轻量滑点扰动不是当前低频定投框架的主要敏感源。

## 7. 对当前默认值稳健性的总体判断
- 结论标签: 中性可用
- baseline 是否处于多数扰动结果的中间区域: 否
- baseline 在部分指标上带有方向性偏好，因此更像中性默认值，而不是严格的中位解。
- 本轮没有出现“轻微改动后全面明显更优”的成功参数组。
- 成功扰动组 6 个，失败组 1 个；失败组不会推翻已有结论，但会降低部分结论强度。
