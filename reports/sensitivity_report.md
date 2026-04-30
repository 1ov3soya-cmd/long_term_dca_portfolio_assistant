# 参数敏感性测试报告

## 测试目的说明
- 本轮不是寻优，而是稳健性检查。
- 当前系统定位仍然是长期定投研究工具，不是短线择时或自动交易系统。

## Baseline 配置摘要
- group_name: baseline
- adjustment_mode: forward
- etf_yellow: 0.15
- etf_red: 0.25
- stock_yellow: 0.12
- stock_red: 0.2
- monthly_buy_rule: first_trading_day

## 参数组列表
```text
group_name,description,adjustment_mode,monthly_buy_rule,status,error
baseline,默认基准参数组,forward,first_trading_day,success,
adj_none,仅切换为不复权，其余保持 baseline,,,failed,"eFinance 获取历史行情失败: symbol=510300, asset_type=etf, error=HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf11%2Cf12%2Cf13&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&beg=20190101&end=20251231&rtntype=6&secid=1.510300&klt=101&fqt=0 (Caused by ProxyError('Unable to connect to proxy', NewConnectionError(""HTTPSConnection(host='127.0.0.1', port=9): Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。"")))"
etf_redline_tighter,仅收紧 ETF 红线到 0.12 / 0.20,forward,first_trading_day,success,
etf_redline_looser,仅放宽 ETF 红线到 0.18 / 0.30,forward,first_trading_day,success,
stock_redline_tighter,仅收紧股票红线到 0.10 / 0.18,forward,first_trading_day,success,
stock_redline_looser,仅放宽股票红线到 0.15 / 0.25,forward,first_trading_day,success,
monthly_buy_last_trading_day,仅切换月度正式买入日为每月最后一个交易日,forward,last_trading_day,success,
higher_slippage,轻量滑点敏感性：ETF 0.15%，股票 0.30%,forward,first_trading_day,success,
```

## 关键指标总表
```text
group_name,annualized_return,max_drawdown,invested_ratio,total_red_triggers,unfilled_amount,average_weight_deviation,status
baseline,0.053222661496830304,0.20476984518500582,0.7677480862261905,326.0,168177.20999712482,0.05926829328140419,success
adj_none,,,,,,,failed
etf_redline_tighter,0.048167143780004196,0.19408191276115705,0.7127497764880952,398.0,168993.2804582441,0.05951605790112617,success
etf_redline_looser,0.05297364730388199,0.20868741279369155,0.768865846952381,226.0,168427.88741725788,0.05497999478307287,success
stock_redline_tighter,0.053222661496830304,0.20476984518500582,0.7677480862261905,326.0,168177.20999712482,0.05926829328140419,success
stock_redline_looser,0.053222661496830304,0.20476984518500582,0.7677480862261905,326.0,168177.20999712482,0.05926829328140419,success
monthly_buy_last_trading_day,0.05204859909161352,0.20521638120430266,0.7682046313452379,302.0,168639.0520970093,0.059360103614274067,success
higher_slippage,0.05323383763959222,0.20485909937819793,0.7678526275476192,326.0,168154.79011814104,0.05926479805064143,success
```

## 与 Baseline 的差异分析
- 收益最敏感参数组: stock_redline_tighter (annualized_return_diff=0.000000)
- 最大回撤最敏感参数组: stock_redline_tighter (max_drawdown_diff=0.000000)
- 红线触发最敏感参数组: higher_slippage (total_red_triggers_diff=0.000000)
- 现金拖累最敏感参数组: stock_redline_tighter (total_uninvested_cash_diff=0.000000)
- 影响较小的参数组: baseline

## 结论与建议
- baseline 年化收益 0.0532，最大回撤 0.2048。
- 建议保留 forward 作为默认复权模式。
- 基准月度买入规则当前为 first_trading_day，如无明显收益/回撤优势，不建议轻易改成其他规则。
- 红线阈值若明显增加现金拖累或红线次数，说明参数可能过紧；若回撤显著放大，则说明参数可能过松。

## 失败组
```text
group_name,description,error
adj_none,仅切换为不复权，其余保持 baseline,"eFinance 获取历史行情失败: symbol=510300, asset_type=etf, error=HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf11%2Cf12%2Cf13&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&beg=20190101&end=20251231&rtntype=6&secid=1.510300&klt=101&fqt=0 (Caused by ProxyError('Unable to connect to proxy', NewConnectionError(""HTTPSConnection(host='127.0.0.1', port=9): Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。"")))"
```

## 限制说明
- 结果受真实数据可用性影响。
- 某些标的历史起点较晚，会影响资金利用率和现金拖累。
- 当前仍是 MVP 级市场摩擦建模，不等于真实成交还原。
- 当前未启用自动卖出，红线主要用于提醒、暂停新增和人工复核。