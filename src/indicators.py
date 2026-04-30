"""指标计算工具。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def moving_average(series: pd.Series, window: int) -> pd.Series:
    """计算简单移动平均线。"""

    return series.rolling(window=window, min_periods=1).mean()


def drawdown_from_high(series: pd.Series) -> pd.Series:
    """计算相对历史高点的回撤比例。"""

    rolling_high = series.cummax()
    return (rolling_high - series) / rolling_high.replace(0, np.nan)


def current_drawdown_from_high(series: pd.Series) -> float:
    """返回当前回撤比例。"""

    if series.empty:
        return 0.0
    return float(drawdown_from_high(series).iloc[-1])


def max_drawdown(series: pd.Series) -> float:
    """返回最大回撤。"""

    if series.empty:
        return 0.0
    return float(drawdown_from_high(series).max())


def annualized_return(nav_series: pd.Series, trading_days_per_year: int = 252) -> float:
    """按交易日估算年化收益。"""

    clean = nav_series.dropna()
    if len(clean) < 2 or clean.iloc[0] <= 0:
        return 0.0

    periods = len(clean) - 1
    years = periods / trading_days_per_year
    if years <= 0:
        return 0.0
    return float((clean.iloc[-1] / clean.iloc[0]) ** (1 / years) - 1)


def annualized_volatility(nav_series: pd.Series, trading_days_per_year: int = 252) -> float:
    """按交易日估算年化波动率。"""

    returns = nav_series.pct_change().dropna()
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=0) * np.sqrt(trading_days_per_year))
