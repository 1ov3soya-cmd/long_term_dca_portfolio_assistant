"""eFinance 真实行情 provider。

说明：
- 当前版本优先统一使用 `efinance.stock.get_quote_history` 获取 ETF 与股票历史日线。
- 已通过真实探针确认：`fund.get_quote_history` 与 `stock.get_quote_history` 的签名不同，
  前者不接受 `beg/end/klt/fqt`，因此不作为历史回测主入口。
- 通过运行时注入 `efinance.config`，将其内部缓存目录重定向到项目内可写目录，
  避免在 site-packages 下写缓存导致权限错误。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any
import sys
import types

import pandas as pd

from src.providers.base_provider import BaseMarketDataProvider
from src.utils.exceptions import ConfigError, DataProviderError
from src.utils.logger import get_logger


@dataclass(slots=True)
class EFinanceProviderConfigV2:
    """eFinance provider 配置。"""

    project_root: str
    max_retry: int = 3
    retry_sleep_seconds: float = 1.5
    log_level: str = "INFO"
    adjustment_mode: str = "forward"
    preferred_history_api: str = "stock"


class EFinanceMarketDataProviderV2(BaseMarketDataProvider):
    """eFinance 历史行情 provider。"""

    EXPECTED_RAW_COLUMNS = [
        "股票名称",
        "股票代码",
        "日期",
        "开盘",
        "收盘",
        "最高",
        "最低",
        "成交量",
        "成交额",
        "振幅",
        "涨跌幅",
        "涨跌额",
        "换手率",
    ]
    FIELD_MAPPING = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "股票名称": "name",
        "股票代码": "symbol",
        "涨跌幅": "pct_chg",
        "涨跌额": "chg",
        "换手率": "turnover_rate",
        "振幅": "amplitude",
    }
    REQUIRED_COLUMNS = ["date", "open", "high", "low", "close"]
    ADJUSTMENT_TO_FQT = {"none": 0, "forward": 1, "backward": 2}

    def __init__(self, config: EFinanceProviderConfigV2) -> None:
        self.config = config
        self.project_root = Path(config.project_root)
        self.logger = get_logger(self.__class__.__name__, config.log_level)
        if config.preferred_history_api != "stock":
            self.logger.warning(
                "当前版本仅验证了 stock.get_quote_history 可稳定拉取 ETF/股票历史，"
                "将忽略 preferred_history_api=%s 并继续使用 stock 接口。",
                config.preferred_history_api,
            )
        self.source_api = "stock.get_quote_history"
        self.runtime_cache_dir = self.project_root / "data" / "provider_state" / "efinance"
        self.runtime_cache_dir.mkdir(parents=True, exist_ok=True)
        self.last_raw_diagnostics: dict[str, Any] = {}
        self.ef = self._import_efinance()

    @property
    def name(self) -> str:
        return "efinance"

    @property
    def adjustment_mode(self) -> str:
        return self.config.adjustment_mode

    @property
    def cache_variant(self) -> str:
        return self.adjustment_mode

    @property
    def expected_raw_columns(self) -> list[str]:
        return list(self.EXPECTED_RAW_COLUMNS)

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        fqt = self._resolve_fqt()
        beg = pd.Timestamp(start_date).strftime("%Y%m%d")
        end = pd.Timestamp(end_date).strftime("%Y%m%d")
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retry + 1):
            try:
                raw = self.ef.stock.get_quote_history(symbol, beg=beg, end=end, klt=101, fqt=fqt)
                self.last_raw_diagnostics = self.diagnose_raw_history(raw, symbol=symbol, asset_type=asset_type)
                standardized = self.standardize_history(raw, symbol=symbol, asset_type=asset_type)
                if standardized.empty:
                    raise DataProviderError(f"eFinance 返回空数据: {symbol}")
                return standardized
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self.logger.warning(
                    "eFinance 获取失败: symbol=%s, asset_type=%s, attempt=%s/%s, error=%s",
                    symbol,
                    asset_type,
                    attempt,
                    self.config.max_retry,
                    exc,
                )
                if attempt < self.config.max_retry:
                    sleep(self.config.retry_sleep_seconds)

        raise DataProviderError(
            f"eFinance 获取历史行情失败: symbol={symbol}, asset_type={asset_type}, error={last_error}"
        ) from last_error

    def diagnose_raw_history(self, raw: Any, symbol: str, asset_type: str) -> dict[str, Any]:
        """输出原始字段诊断。"""

        frame = self._unwrap_dataframe(raw)
        date_series = frame.iloc[:, 2].astype(str) if not frame.empty and len(frame.columns) >= 3 else pd.Series(dtype=str)
        return {
            "symbol": symbol,
            "asset_type": asset_type,
            "provider": self.name,
            "source_api": self.source_api,
            "adjustment_mode": self.adjustment_mode,
            "rows": len(frame),
            "columns": list(frame.columns),
            "head": frame.head(2).to_dict(orient="records"),
            "tail": frame.tail(2).to_dict(orient="records"),
            "sorted": bool(date_series.is_monotonic_increasing) if not frame.empty else True,
            "duplicate_dates": int(date_series.duplicated().sum()) if not frame.empty else 0,
            "nulls": frame.isna().sum().to_dict() if not frame.empty else {},
        }

    def standardize_history(self, raw: Any, symbol: str, asset_type: str) -> pd.DataFrame:
        """将 eFinance 原始结果标准化为项目统一字段。"""

        frame = self._unwrap_dataframe(raw).copy()
        if frame.empty:
            raise DataProviderError(f"eFinance 返回空表: {symbol}")

        renamed = frame.rename(columns=self.FIELD_MAPPING)
        missing_columns = [column for column in self.REQUIRED_COLUMNS if column not in renamed.columns]
        if missing_columns:
            diagnostics = self.diagnose_raw_history(frame, symbol=symbol, asset_type=asset_type)
            self.logger.error("eFinance 字段诊断: %s", diagnostics)
            raise DataProviderError(
                f"eFinance 返回字段不符合预期，缺少字段: {missing_columns}。"
                "已输出字段诊断，请人工确认后再调整映射。"
            )

        renamed["date"] = pd.to_datetime(renamed["date"]).dt.normalize()
        renamed["symbol"] = str(symbol).zfill(6)
        renamed["asset_type"] = asset_type

        numeric_columns = ["open", "high", "low", "close", "volume", "amount", "pct_chg", "chg", "turnover_rate", "amplitude"]
        for column in numeric_columns:
            if column in renamed.columns:
                renamed[column] = pd.to_numeric(renamed[column], errors="coerce")

        renamed["adj_close"] = renamed["close"]
        renamed["adjustment_mode"] = self.adjustment_mode
        renamed["source_api"] = self.source_api

        standardized_columns = [
            "date",
            "symbol",
            "asset_type",
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
            "amount",
            "pct_chg",
            "chg",
            "turnover_rate",
            "amplitude",
            "adjustment_mode",
            "source_api",
        ]
        if "name" in renamed.columns:
            standardized_columns.insert(3, "name")

        standardized = renamed[[column for column in standardized_columns if column in renamed.columns]].copy()
        standardized = standardized.dropna(subset=["date", "open", "high", "low", "close"])
        standardized["symbol"] = standardized["symbol"].astype(str).str.zfill(6)
        standardized = standardized.sort_values("date")
        standardized = standardized.drop_duplicates(subset=["date", "symbol", "asset_type"], keep="last")
        return standardized.reset_index(drop=True)

    def _resolve_fqt(self) -> int:
        if self.adjustment_mode not in self.ADJUSTMENT_TO_FQT:
            raise ConfigError(f"不支持的 adjustment_mode: {self.adjustment_mode}")
        return self.ADJUSTMENT_TO_FQT[self.adjustment_mode]

    def _import_efinance(self) -> Any:
        """导入 eFinance，并将其内部缓存路径指向项目内可写目录。"""

        injected = types.ModuleType("efinance.config")
        injected.HERE = self.runtime_cache_dir
        injected.DATA_DIR = self.runtime_cache_dir
        injected.SEARCH_RESULT_CACHE_PATH = str(self.runtime_cache_dir / "search-cache.json")
        injected.MAX_CONNECTIONS = 20
        injected.SHOW_TICKFLOW_PROMPT = False
        sys.modules["efinance.config"] = injected

        try:
            import efinance as ef  # type: ignore
        except ImportError as exc:
            raise DataProviderError(
                "efinance 未安装或不可导入。请先安装依赖，或改用 demo 模式。"
            ) from exc
        return ef

    @staticmethod
    def _unwrap_dataframe(raw: Any) -> pd.DataFrame:
        """从不同返回结构中提取 DataFrame。"""

        if isinstance(raw, pd.DataFrame):
            return raw
        if isinstance(raw, dict):
            for value in raw.values():
                if isinstance(value, pd.DataFrame):
                    return value
        if isinstance(raw, list) and raw and isinstance(raw[0], pd.DataFrame):
            return raw[0]
        raise DataProviderError(f"无法从 eFinance 返回值中提取 DataFrame: {type(raw)}")
