"""数据加载与增量更新。"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data_cache import DataCache
from src.providers.base_provider import BaseMarketDataProvider
from src.providers.efinance_provider_v2 import (
    EFinanceMarketDataProviderV2,
    EFinanceProviderConfigV2,
)
from src.utils.calendar_utils import build_calendar_from_histories, resolve_latest_trading_day
from src.utils.config_loader import load_all_configs
from src.utils.exceptions import ConfigError, DataProviderError
from src.utils.logger import get_logger
from src.utils.runtime_models import DataDiagnostic, MarketDataBundle


class MarketDataLoader:
    """封装 provider、缓存和增量更新逻辑。"""

    def __init__(self, project_root: str | Path, configs: dict[str, dict[str, Any]] | None = None) -> None:
        self.project_root = Path(project_root)
        self.configs = configs or load_all_configs(self.project_root / "config")
        app_cfg = self.configs["app"]
        self.logger = get_logger(self.__class__.__name__, app_cfg["runtime"]["log_level"])
        self.cache = DataCache(
            root_dir=self.project_root / app_cfg["paths"]["cache_data_dir"],
            cache_format=app_cfg["runtime"]["cache_format"],
            log_level=app_cfg["runtime"]["log_level"],
        )
        self.provider_name = app_cfg["runtime"]["data_provider"]
        self.app_cfg = app_cfg
        self.provider: BaseMarketDataProvider | None = None

    def _adjustment_mode(self) -> str:
        return self.app_cfg.get("efinance", {}).get("adjustment_mode", "forward")

    def _build_provider(self) -> BaseMarketDataProvider:
        if self.provider_name == "efinance":
            return EFinanceMarketDataProviderV2(
                EFinanceProviderConfigV2(
                    project_root=str(self.project_root),
                    max_retry=self.app_cfg["runtime"]["max_retry"],
                    retry_sleep_seconds=self.app_cfg["runtime"]["retry_sleep_seconds"],
                    log_level=self.app_cfg["runtime"]["log_level"],
                    adjustment_mode=self._adjustment_mode(),
                    preferred_history_api=self.app_cfg.get("efinance", {}).get("preferred_history_api", "stock"),
                )
            )
        raise ConfigError(f"暂不支持的 provider: {self.provider_name}")

    def get_provider(self) -> BaseMarketDataProvider:
        """懒加载 provider，确保 demo 模式不强依赖真实接口。"""

        if self.provider is None:
            self.provider = self._build_provider()
        return self.provider

    def load_symbol_history(
        self,
        symbol: str,
        asset_type: str,
        start_date: str,
        end_date: str,
        use_incremental: bool = True,
    ) -> pd.DataFrame:
        """加载单个标的历史行情，优先使用缓存并支持增量更新。"""

        variant = self._adjustment_mode()
        existing = self.cache.load(symbol, asset_type, variant=variant)
        fetch_start = start_date

        if use_incremental and not existing.empty:
            last_date = pd.Timestamp(existing["date"].max()).normalize()
            next_date = last_date + pd.Timedelta(days=1)
            fetch_start = max(pd.Timestamp(start_date), next_date).strftime("%Y-%m-%d")

        incoming = pd.DataFrame()
        if pd.Timestamp(fetch_start) <= pd.Timestamp(end_date):
            try:
                incoming = self.get_provider().fetch_history(symbol, asset_type, fetch_start, end_date)
            except DataProviderError:
                if existing.empty:
                    raise
                self.logger.warning("provider 获取失败，回退到本地缓存: %s", symbol)

        merged = self.cache.merge(existing, incoming)
        if not merged.empty:
            self.cache.save(symbol, asset_type, merged, variant=variant)

        mask = (merged["date"] >= pd.Timestamp(start_date)) & (merged["date"] <= pd.Timestamp(end_date))
        return merged.loc[mask].sort_values("date").reset_index(drop=True)

    def load_market_data_bundle(
        self,
        start_date: str,
        end_date: str,
        mode: str = "real",
    ) -> MarketDataBundle:
        """加载完整标的池，并返回历史数据、诊断和元信息。"""

        universe = self.build_universe()
        if mode == "demo":
            histories = self.build_demo_history(universe, start_date, end_date)
            calendar = build_calendar_from_histories(histories, self.configs["universe"]["universe"]["benchmark_symbol"])
            diagnostics = self._build_demo_diagnostics(histories)
            metadata = {
                "data_mode": "demo",
                "provider": "demo",
                "adjustment_mode": "demo",
                "latest_data_date": calendar[-1].strftime("%Y-%m-%d") if calendar else None,
                "data_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "calendar_inferred_from": "demo_histories",
                "config_summary": self._build_config_summary(),
            }
            self._write_data_diagnostics(diagnostics, metadata)
            return MarketDataBundle(histories=histories, diagnostics=diagnostics, calendar=calendar, metadata=metadata)

        histories: dict[str, pd.DataFrame] = {}
        diagnostics: list[DataDiagnostic] = []
        provider = self.get_provider()
        for item in universe:
            symbol = item["symbol"]
            asset_type = item["asset_type"]
            variant = self._adjustment_mode()
            cache_before = self.cache.load(symbol, asset_type, variant=variant)
            cache_hit = not cache_before.empty
            fallback_used = False
            note = ""
            try:
                history = self.load_symbol_history(symbol, asset_type, start_date, end_date, use_incremental=True)
                if history.empty:
                    note = "返回空数据"
            except DataProviderError as exc:
                history = cache_before.copy()
                fallback_used = not history.empty
                note = f"provider_error={exc}"
                if history.empty:
                    raise
            histories[symbol] = history
            cache_path = self.cache.cache_path(symbol, asset_type, variant=variant)
            latest_update = (
                datetime.fromtimestamp(cache_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                if cache_path.exists()
                else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            raw_columns = []
            if hasattr(provider, "last_raw_diagnostics") and symbol == getattr(provider, "last_raw_diagnostics", {}).get("symbol"):
                raw_columns = list(getattr(provider, "last_raw_diagnostics", {}).get("columns", []))
            elif hasattr(provider, "expected_raw_columns"):
                raw_columns = list(getattr(provider, "expected_raw_columns"))
            diagnostics.append(
                self._build_diagnostic(
                    symbol=symbol,
                    asset_type=asset_type,
                    history=history,
                    provider_name=provider.name,
                    source_api=getattr(provider, "source_api", "unknown"),
                    adjustment_mode=getattr(provider, "adjustment_mode", variant),
                    cache_variant=variant,
                    fallback_used=fallback_used,
                    cache_hit=cache_hit,
                    note=note,
                    raw_columns=raw_columns,
                    latest_update=latest_update,
                )
            )

        calendar = build_calendar_from_histories(histories, self.configs["universe"]["universe"]["benchmark_symbol"])
        latest_data_date = calendar[-1].strftime("%Y-%m-%d") if calendar else None
        diagnostics_frame = pd.DataFrame([item.to_dict() for item in diagnostics])
        metadata = {
            "data_mode": "real",
            "provider": provider.name,
            "adjustment_mode": getattr(provider, "adjustment_mode", self._adjustment_mode()),
            "source_api": getattr(provider, "source_api", "unknown"),
            "latest_data_date": latest_data_date,
            "data_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "calendar_inferred_from": self.configs["universe"]["universe"]["benchmark_symbol"],
            "config_summary": self._build_config_summary(),
            "as_of_date": resolve_latest_trading_day(calendar, end_date).strftime("%Y-%m-%d") if calendar else end_date,
        }
        diagnostics_paths = self._write_data_diagnostics(diagnostics_frame, metadata)
        metadata["diagnostics_paths"] = {key: str(value) for key, value in diagnostics_paths.items()}
        return MarketDataBundle(histories=histories, diagnostics=diagnostics_frame, calendar=calendar, metadata=metadata)

    def load_universe_history(self, universe: list[dict[str, str]], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
        """批量加载标的池历史行情。"""

        data: dict[str, pd.DataFrame] = {}
        for item in universe:
            data[item["symbol"]] = self.load_symbol_history(
                symbol=item["symbol"],
                asset_type=item["asset_type"],
                start_date=start_date,
                end_date=end_date,
                use_incremental=self.configs["app"]["runtime"]["enable_incremental_update"],
            )
        return data

    def build_universe(self) -> list[dict[str, str]]:
        """从配置生成完整标的池。"""

        universe: list[dict[str, str]] = []
        for item in self.configs["portfolio"]["etf_pool"]:
            universe.append({"symbol": item["symbol"], "asset_type": "etf"})
        for item in self.configs["portfolio"]["stock_pool"]:
            universe.append({"symbol": item["symbol"], "asset_type": "stock"})
        return universe

    @staticmethod
    def build_demo_history(
        universe: list[dict[str, str]],
        start_date: str,
        end_date: str,
    ) -> dict[str, pd.DataFrame]:
        """构造最小可运行 demo 数据。

        说明：
        - 仅用于离线演示与测试。
        - 正式使用仍应优先走 e-finance 或本地真实历史数据。
        """

        dates = pd.bdate_range(start=start_date, end=end_date)
        data: dict[str, pd.DataFrame] = {}

        for index, item in enumerate(universe):
            rng = np.random.default_rng(seed=index + 7)
            base_price = 50 + index * 20
            drift = 0.0003 if item["asset_type"] == "etf" else 0.0004
            shocks = rng.normal(loc=drift, scale=0.012, size=len(dates))
            close = base_price * np.exp(np.cumsum(shocks))
            frame = pd.DataFrame(
                {
                    "date": dates,
                    "symbol": item["symbol"],
                    "asset_type": item["asset_type"],
                    "open": close * (1 - 0.002),
                    "high": close * (1 + 0.006),
                    "low": close * (1 - 0.006),
                    "close": close,
                    "volume": rng.integers(1_000_000, 10_000_000, size=len(dates)),
                    "amount": close * rng.integers(100_000, 500_000, size=len(dates)),
                }
            )
            data[item["symbol"]] = frame
        return data

    def _build_diagnostic(
        self,
        symbol: str,
        asset_type: str,
        history: pd.DataFrame,
        provider_name: str,
        source_api: str,
        adjustment_mode: str,
        cache_variant: str,
        fallback_used: bool,
        cache_hit: bool,
        note: str,
        raw_columns: list[str] | None = None,
        latest_update: str | None = None,
    ) -> DataDiagnostic:
        if history.empty:
            return DataDiagnostic(
                symbol=symbol,
                asset_type=asset_type,
                provider=provider_name,
                source_api=source_api,
                adjustment_mode=adjustment_mode,
                cache_variant=cache_variant,
                rows=0,
                start_date=None,
                end_date=None,
                sorted_ok=True,
                duplicate_dates=0,
                missing_required_rows=0,
                raw_columns=raw_columns or [],
                standardized_columns=[],
                fallback_used=fallback_used,
                cache_hit=cache_hit,
                latest_update=latest_update or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                note=note or "empty_history",
            )

        required = ["date", "open", "high", "low", "close"]
        missing_required_rows = int(history[required].isna().any(axis=1).sum())
        sorted_ok = bool(pd.to_datetime(history["date"]).is_monotonic_increasing)
        duplicate_dates = int(pd.to_datetime(history["date"]).duplicated().sum())
        return DataDiagnostic(
            symbol=symbol,
            asset_type=asset_type,
            provider=provider_name,
            source_api=source_api,
            adjustment_mode=adjustment_mode,
            cache_variant=cache_variant,
            rows=len(history),
            start_date=pd.Timestamp(history["date"].min()).strftime("%Y-%m-%d"),
            end_date=pd.Timestamp(history["date"].max()).strftime("%Y-%m-%d"),
            sorted_ok=sorted_ok,
            duplicate_dates=duplicate_dates,
            missing_required_rows=missing_required_rows,
            raw_columns=raw_columns or [],
            standardized_columns=list(history.columns),
            fallback_used=fallback_used,
            cache_hit=cache_hit,
            latest_update=latest_update or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            note=note,
        )

    def _build_demo_diagnostics(self, histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        diagnostics = [
            self._build_diagnostic(
                symbol=symbol,
                asset_type=str(frame["asset_type"].iloc[0]) if not frame.empty else "unknown",
                history=frame,
                provider_name="demo",
                source_api="synthetic_generator",
                adjustment_mode="demo",
                cache_variant="demo",
                fallback_used=False,
                cache_hit=False,
                note="synthetic_data",
            ).to_dict()
            for symbol, frame in histories.items()
        ]
        return pd.DataFrame(diagnostics)

    def _write_data_diagnostics(self, diagnostics: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Path]:
        reports_dir = self.project_root / "reports" / "data"
        reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = reports_dir / f"data_diagnostics_{stamp}.csv"
        json_path = reports_dir / f"data_diagnostics_{stamp}.json"
        diagnostics.to_csv(csv_path, index=False, encoding="utf-8-sig")
        payload = {
            "metadata": metadata,
            "diagnostics": diagnostics.to_dict(orient="records"),
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
        return {"csv": csv_path, "json": json_path}

    def _build_config_summary(self) -> dict[str, Any]:
        return {
            "monthly_budget": self.configs["portfolio"]["portfolio"]["monthly_budget"],
            "etf_total_weight": self.configs["portfolio"]["asset_allocation"]["etf_total_weight"],
            "stock_total_weight": self.configs["portfolio"]["asset_allocation"]["stock_total_weight"],
            "adjustment_mode": self._adjustment_mode(),
            "min_trade_lot": self.configs["backtest"]["trading_rules"]["min_trade_lot"],
            "monthly_rule": self.configs["app"]["schedule"]["monthly_invest_day_rule"],
            "weekly_rule": self.configs["app"]["schedule"]["weekly_risk_check_rule"],
        }
