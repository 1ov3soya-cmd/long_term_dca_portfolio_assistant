"""交易日期相关工具。"""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


def to_timestamp(value: str | pd.Timestamp) -> pd.Timestamp:
    """统一转换为 Timestamp。"""

    return pd.Timestamp(value).normalize()


def normalize_calendar(dates: Iterable[str | pd.Timestamp]) -> pd.DatetimeIndex:
    """将日期序列标准化为升序 DatetimeIndex。"""

    calendar = pd.DatetimeIndex(sorted({to_timestamp(value) for value in dates}))
    return calendar


def first_trading_day_each_month(calendar: Sequence[str | pd.Timestamp]) -> list[pd.Timestamp]:
    """根据给定交易日历，提取每个月的第一个交易日。"""

    index = normalize_calendar(calendar)
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("M")).first())


def last_trading_day_each_week(calendar: Sequence[str | pd.Timestamp]) -> list[pd.Timestamp]:
    """根据给定交易日历，提取每周最后一个交易日。"""

    index = normalize_calendar(calendar)
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("W-FRI")).last())


def clamp_history(df: pd.DataFrame, end_date: str | pd.Timestamp) -> pd.DataFrame:
    """截取截至指定日期的历史数据。"""

    ts = to_timestamp(end_date)
    return df.loc[df["date"] <= ts].copy()
