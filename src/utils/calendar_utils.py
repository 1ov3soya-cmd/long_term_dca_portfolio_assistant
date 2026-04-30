"""交易日历扩展工具。"""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


def to_timestamp(value: str | pd.Timestamp) -> pd.Timestamp:
    """统一转换为标准化交易日期。"""

    return pd.Timestamp(value).normalize()


def normalize_calendar(dates: Iterable[str | pd.Timestamp]) -> pd.DatetimeIndex:
    """将日期序列标准化为去重升序交易日历。"""

    return pd.DatetimeIndex(sorted({to_timestamp(value) for value in dates}))


def build_calendar_from_histories(
    histories: dict[str, pd.DataFrame],
    preferred_symbol: str | None = None,
) -> list[pd.Timestamp]:
    """根据真实行情推导近似交易日历。"""

    if preferred_symbol and preferred_symbol in histories and not histories[preferred_symbol].empty:
        return list(normalize_calendar(histories[preferred_symbol]["date"].tolist()))

    dates: list[pd.Timestamp] = []
    for frame in histories.values():
        if frame.empty or "date" not in frame.columns:
            continue
        dates.extend(pd.to_datetime(frame["date"]).dt.normalize().tolist())
    return list(normalize_calendar(dates))


def first_trading_day_each_month(calendar: Sequence[str | pd.Timestamp]) -> list[pd.Timestamp]:
    """提取每个月第一个交易日。"""

    index = normalize_calendar(calendar)
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("M")).first())


def last_trading_day_each_month(calendar: Sequence[str | pd.Timestamp]) -> list[pd.Timestamp]:
    """提取每个月最后一个交易日。"""

    index = normalize_calendar(calendar)
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("M")).last())


def last_trading_day_each_week(calendar: Sequence[str | pd.Timestamp]) -> list[pd.Timestamp]:
    """提取每周最后一个交易日。"""

    index = normalize_calendar(calendar)
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("W-FRI")).last())


def resolve_latest_trading_day(
    calendar: Sequence[str | pd.Timestamp],
    target_date: str | pd.Timestamp,
) -> pd.Timestamp:
    """将目标日期映射为不晚于该日期的最近交易日。"""

    index = normalize_calendar(calendar)
    target = to_timestamp(target_date)
    eligible = index[index <= target]
    if len(eligible) == 0:
        raise ValueError(f"未找到不晚于 {target.date()} 的交易日。")
    return pd.Timestamp(eligible[-1]).normalize()
