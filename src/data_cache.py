"""本地缓存层。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.exceptions import CacheError
from src.utils.logger import get_logger


class DataCache:
    """负责历史行情的本地缓存与增量合并。"""

    def __init__(self, root_dir: str | Path, cache_format: str = "csv", log_level: str = "INFO") -> None:
        self.root_dir = Path(root_dir)
        self.cache_format = cache_format.lower()
        self.logger = get_logger(self.__class__.__name__, log_level)

    def cache_path(self, symbol: str, asset_type: str, variant: str = "") -> Path:
        """返回指定标的缓存路径。"""

        suffix = ".parquet" if self.cache_format == "parquet" else ".csv"
        variant_suffix = f"_{variant}" if variant else ""
        return self.root_dir / asset_type / f"{symbol}{variant_suffix}{suffix}"

    def load(self, symbol: str, asset_type: str, variant: str = "") -> pd.DataFrame:
        """读取缓存，如果不存在则返回空表。"""

        path = self.cache_path(symbol, asset_type, variant)
        if not path.exists():
            return pd.DataFrame()

        try:
            if path.suffix == ".parquet":
                df = pd.read_parquet(path)
            else:
                dtype_mapping = {"symbol": "string", "asset_type": "string"}
                df = pd.read_csv(path, parse_dates=["date"], dtype=dtype_mapping)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            if "symbol" in df.columns:
                df["symbol"] = df["symbol"].astype(str).str.zfill(6)
            if "asset_type" in df.columns:
                df["asset_type"] = df["asset_type"].astype(str)
            return df.sort_values("date").reset_index(drop=True)
        except Exception as exc:  # noqa: BLE001
            raise CacheError(f"缓存读取失败: {path}") from exc

    def save(self, symbol: str, asset_type: str, df: pd.DataFrame, variant: str = "") -> Path:
        """保存缓存。"""

        path = self.cache_path(symbol, asset_type, variant)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.suffix == ".parquet":
                df.to_parquet(path, index=False)
            else:
                df.to_csv(path, index=False, encoding="utf-8-sig")
            return path
        except Exception as exc:  # noqa: BLE001
            raise CacheError(f"缓存保存失败: {path}") from exc

    def merge(self, existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
        """合并缓存与新数据。"""

        if existing.empty:
            merged = incoming.copy()
        elif incoming.empty:
            merged = existing.copy()
        else:
            merged = pd.concat([existing, incoming], ignore_index=True)

        if merged.empty:
            return merged

        merged["date"] = pd.to_datetime(merged["date"]).dt.normalize()
        if "symbol" in merged.columns:
            merged["symbol"] = merged["symbol"].astype(str).str.zfill(6)
        if "asset_type" in merged.columns:
            merged["asset_type"] = merged["asset_type"].astype(str)

        dedupe_keys = ["date", "symbol"]
        if "asset_type" in merged.columns:
            dedupe_keys.append("asset_type")
        merged = merged.drop_duplicates(subset=dedupe_keys, keep="last")
        return merged.sort_values("date").reset_index(drop=True)

    def last_date(self, symbol: str, asset_type: str, variant: str = "") -> pd.Timestamp | None:
        """返回缓存最后日期。"""

        df = self.load(symbol, asset_type, variant)
        if df.empty:
            return None
        return pd.Timestamp(df["date"].max()).normalize()
