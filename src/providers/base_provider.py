"""数据提供层抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseMarketDataProvider(ABC):
    """行情数据提供层基类。"""

    @abstractmethod
    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取标准化后的历史行情。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """返回 provider 名称。"""
