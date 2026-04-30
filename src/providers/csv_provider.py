"""本地 CSV 数据提供层。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.providers.base_provider import BaseMarketDataProvider
from src.utils.exceptions import DataProviderError


class CsvMarketDataProvider(BaseMarketDataProvider):
    """从本地 CSV 读取历史行情。"""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)

    @property
    def name(self) -> str:
        return "csv"

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        file_path = self.root_dir / asset_type / f"{symbol}.csv"
        if not file_path.exists():
            raise DataProviderError(f"本地 CSV 不存在: {file_path}")

        df = pd.read_csv(file_path, parse_dates=["date"])
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        mask = (df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))
        return df.loc[mask].sort_values("date").reset_index(drop=True)
