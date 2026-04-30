# 数据验收报告

## 数据模式
- 模式: real
- provider: efinance
- source_api: stock.get_quote_history
- adjustment_mode: forward
- latest_data_date: 2025-12-31
- data_updated_at: 2026-03-31 21:07:41

## 标的级摘要
```text
symbol,asset_type,provider,source_api,adjustment_mode,first_available_date,last_available_date,total_samples,coverage_ratio,missing_rows,duplicate_dates,non_increasing_dates,price_missing_rows,volume_missing_rows,amount_missing_rows,latest_cache_update,data_access_path,coverage_start_ok,missing_start_period,cache_hit
510300,etf,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
510500,etf,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
515180,etf,efinance,stock.get_quote_history,forward,2019-12-20,2025-12-31,1463,0.8611,236,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,False,2019-01-02 ~ 2019-12-19,True
518880,etf,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
600519,stock,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
000858,stock,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
600036,stock,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
000333,stock,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1688,0.9935,11,0,False,0,0,0,2026-03-31 21:07:40,provider_refresh_or_cache_hit,True,,True
601318,stock,efinance,stock.get_quote_history,forward,2019-01-02,2025-12-31,1699,1.0,0,0,False,0,0,0,2026-03-31 21:07:41,provider_refresh_or_cache_hit,True,,True
```

## 日期对齐程度
```text
symbol,asset_type,aligned_days,calendar_days,alignment_ratio
510300,etf,1699,1699,1.0
510500,etf,1699,1699,1.0
515180,etf,1463,1699,0.8611
518880,etf,1699,1699,1.0
600519,stock,1699,1699,1.0
000858,stock,1699,1699,1.0
600036,stock,1699,1699,1.0
000333,stock,1688,1699,0.9935
601318,stock,1699,1699,1.0
```

## 覆盖性检查
```text
symbol,asset_type,missing_start_period,current_handling
515180,etf,2019-01-02 ~ 2019-12-19,标的在该时段不可用时，回测保留现金，直到出现可交易数据。
```

## 复权说明
- 当前复权模式: forward
- adj_close 定义: adj_close 当前等于所选复权模式下的 close。
- 缓存隔离: 缓存按复权模式隔离保存，不同复权模式不能直接横向对比。

## 重要限制
- 当前交易日历根据真实行情日期推导，不是交易所官方日历。
- 若标的在回测起点前无数据，系统当前处理为保留现金，直到出现可交易数据。