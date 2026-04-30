"""e-finance 数据提供层。"""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Callable

import pandas as pd

from src.providers.base_provider import BaseMarketDataProvider
from src.utils.exceptions import DataProviderError
from src.utils.logger import get_logger


@dataclass(slots=True)
class EFinanceProviderConfig:
    """e-finance provider 配置。"""

    max_retry: int = 3
    retry_sleep_seconds: float = 1.5
    log_level: str = "INFO"


class EFinanceMarketDataProvider(BaseMarketDataProvider):
    """e-finance 历史行情 provider。

    说明：
    - 第一版优先尝试东财历史行情接口。
    - 若接口字段或返回结构变化，不做静默修复，而是打印字段诊断并抛错，等待人工确认。
    """

    COLUMN_MAPPING = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "股票名称": "name",
        "基金名称": "name",
        "股票代码": "symbol",
        "基金代码": "symbol",
    }

    REQUIRED_COLUMNS = {"date", "open", "high", "low", "close"}

    def __init__(self, config: EFinanceProviderConfig | None = None) -> None:
        self.config = config or EFinanceProviderConfig()
        self.logger = get_logger(self.__class__.__name__, self.config.log_level)
        try:
            import efinance as ef  # type: ignore
        except ImportError as exc:
            raise DataProviderError(
                "e-finance 未安装或不可导入。请先安装 requirements.txt 中依赖，"
                "或切换为 CSV provider。"
            ) from exc
        self.ef = ef

    @property
    def name(self) -> str:
        return "efinance"

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        start_str = pd.Timestamp(start_date).strftime("%Y%m%d")
        end_str = pd.Timestamp(end_date).strftime("%Y%m%d")
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retry + 1):
            try:
                raw = self._call_efinance(symbol, asset_type, start_str, end_str)
                return self._standardize(raw, symbol=symbol, asset_type=asset_type)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self.logger.warning(
                    "e-finance 获取失败: symbol=%s, asset_type=%s, attempt=%s/%s, error=%s",
                    symbol,
                    asset_type,
                    attempt,
                    self.config.max_retry,
                    exc,
                )
                if attempt < self.config.max_retry:
                    sleep(self.config.retry_sleep_seconds)

        raise DataProviderError(
            f"e-finance 获取历史行情失败: {symbol}, {asset_type}, error={last_error}"
        ) from last_error

    def _call_efinance(
        self,
        symbol: str,
        asset_type: str,
        start_str: str,
        end_str: str,
    ) -> Any:
        """尝试多个可能签名，兼容 e-finance 常见版本差异。"""

        call_specs: list[tuple[Callable[..., Any], list[dict[str, Any]]]] = []

        stock_api = getattr(getattr(self.ef, "stock", None), "get_quote_history", None)
        fund_api = getattr(getattr(self.ef, "fund", None), "get_quote_history", None)

        candidate_kwargs = [
            {"stock_codes": symbol, "beg": start_str, "end": end_str, "klt": 101, "fqt": 1},
            {"stock_codes": [symbol], "beg": start_str, "end": end_str, "klt": 101, "fqt": 1},
            {"code": symbol, "beg": start_str, "end": end_str, "klt": 101, "fqt": 1},
            {"codes": [symbol], "beg": start_str, "end": end_str, "klt": 101, "fqt": 1},
        ]

        if asset_type == "etf":
            if fund_api is not None:
                call_specs.append((fund_api, candidate_kwargs))
            if stock_api is not None:
                call_specs.append((stock_api, candidate_kwargs))
        else:
            if stock_api is not None:
                call_specs.append((stock_api, candidate_kwargs))
            if fund_api is not None:
                call_specs.append((fund_api, candidate_kwargs))

        errors: list[str] = []
        for func, kwargs_list in call_specs:
            for kwargs in kwargs_list:
                try:
                    result = func(**kwargs)
                    if result is not None:
                        return result
                except TypeError as exc:
                    errors.append(f"{func.__qualname__} kwargs不兼容: {exc}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{func.__qualname__} 调用失败: {exc}")

        raise DataProviderError(
            f"未找到可用的 e-finance 调用方式。symbol={symbol}, asset_type={asset_type}, "
            f"diagnostics={' | '.join(errors[:6])}"
        )

    def _standardize(self, raw: Any, symbol: str, asset_type: str) -> pd.DataFrame:
        df = self._extract_frame(raw)
        original_columns = list(df.columns)

        renamed = df.rename(columns=self.COLUMN_MAPPING).copy()
        if "date" not in renamed.columns and "日期" in df.columns:
            renamed["date"] = df["日期"]

        missing = self.REQUIRED_COLUMNS - set(renamed.columns)
        if missing:
            diagnostics = {
                "symbol": symbol,
                "asset_type": asset_type,
                "columns": original_columns,
                "sample": df.head(3).to_dict(orient="records"),
            }
            self.logger.error("e-finance 字段诊断: %s", diagnostics)
            raise DataProviderError(
                f"e-finance 返回字段不符合预期，缺少字段: {sorted(missing)}。"
                "已输出字段诊断，请人工确认后再调整映射。"
            )

        renamed["date"] = pd.to_datetime(renamed["date"]).dt.normalize()
        renamed["symbol"] = symbol
        renamed["asset_type"] = asset_type

        for column in ["open", "high", "low", "close", "volume", "amount"]:
            if column in renamed.columns:
                renamed[column] = pd.to_numeric(renamed[column], errors="coerce")

        result_columns = ["date", "symbol", "asset_type", "open", "high", "low", "close"]
        for optional in ["volume", "amount", "name"]:
            if optional in renamed.columns:
                result_columns.append(optional)

        result = renamed[result_columns].dropna(subset=["date", "close"]).sort_values("date")
        return result.reset_index(drop=True)

    @staticmethod
    def _extract_frame(raw: Any) -> pd.DataFrame:
        """从不同结构中提取 DataFrame。"""

        if isinstance(raw, pd.DataFrame):
            return raw
        if isinstance(raw, dict):
            for value in raw.values():
                if isinstance(value, pd.DataFrame):
                    return value
        if isinstance(raw, list) and raw and isinstance(raw[0], pd.DataFrame):
            return raw[0]
        raise DataProviderError(f"无法从 e-finance 返回值中提取 DataFrame: {type(raw)}")
