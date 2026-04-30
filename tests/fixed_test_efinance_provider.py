from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.providers.efinance_provider_v2 import EFinanceMarketDataProviderV2, EFinanceProviderConfigV2
from src.utils.exceptions import DataProviderError
from src.utils.logger import get_logger


def build_provider_without_import() -> EFinanceMarketDataProviderV2:
    provider = object.__new__(EFinanceMarketDataProviderV2)
    provider.config = EFinanceProviderConfigV2(project_root=str(PROJECT_ROOT), adjustment_mode="forward")
    provider.project_root = PROJECT_ROOT
    provider.logger = get_logger("provider_test")
    provider.source_api = "stock.get_quote_history"
    provider.runtime_cache_dir = PROJECT_ROOT / "data" / "processed"
    return provider


def test_standardize_history_normalizes_fields_and_dedupes_dates() -> None:
    provider = build_provider_without_import()
    raw = pd.DataFrame(
        [
            {"股票名称": "样本ETF", "股票代码": "510300", "日期": "2024-01-02", "开盘": 1.0, "收盘": 1.1, "最高": 1.2, "最低": 0.9, "成交量": 10, "成交额": 11},
            {"股票名称": "样本ETF", "股票代码": "510300", "日期": "2024-01-02", "开盘": 1.0, "收盘": 1.15, "最高": 1.2, "最低": 0.9, "成交量": 12, "成交额": 13},
            {"股票名称": "样本ETF", "股票代码": "510300", "日期": "2024-01-03", "开盘": 1.2, "收盘": 1.3, "最高": 1.4, "最低": 1.1, "成交量": 15, "成交额": 18},
        ]
    )

    standardized = provider.standardize_history(raw, symbol="510300", asset_type="etf")

    assert list(standardized.columns[:7]) == ["date", "symbol", "asset_type", "name", "open", "high", "low"]
    assert len(standardized) == 2
    assert "adj_close" in standardized.columns
    assert standardized["close"].iloc[0] == 1.15


def test_standardize_history_rejects_empty_data() -> None:
    provider = build_provider_without_import()
    with pytest.raises(DataProviderError):
        provider.standardize_history(pd.DataFrame(), symbol="510300", asset_type="etf")
