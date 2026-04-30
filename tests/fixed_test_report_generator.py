from pathlib import Path
import shutil
import sys
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.report_generator import ReportGenerator
from src.utils.runtime_models import ExtendedBacktestResult, MarketDataBundle
from src.utils.schemas import AllocationSuggestion, MonthlyRecommendation

TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_bundle() -> MarketDataBundle:
    diagnostics = pd.DataFrame(
        [
            {
                "symbol": "510300",
                "asset_type": "etf",
                "rows": 10,
                "start_date": "2024-01-02",
                "end_date": "2024-03-29",
                "duplicate_dates": 0,
                "missing_required_rows": 0,
                "fallback_used": False,
                "cache_hit": True,
                "latest_update": "2026-03-31 12:00:00",
            }
        ]
    )
    return MarketDataBundle(
        histories={},
        diagnostics=diagnostics,
        calendar=[],
        metadata={
            "data_mode": "real",
            "provider": "efinance",
            "source_api": "stock.get_quote_history",
            "adjustment_mode": "forward",
            "latest_data_date": "2024-03-29",
            "data_updated_at": "2026-03-31 12:00:00",
            "as_of_date": "2024-03-29",
        },
    )


def test_report_generator_real_mode_reports_do_not_crash_fixed() -> None:
    temp_root = TMP_ROOT / f"report_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        generator = ReportGenerator(temp_root)
        recommendation = MonthlyRecommendation(
            as_of_date=pd.Timestamp("2024-03-29"),
            total_budget=10000.0,
            etf_budget=8000.0,
            stock_budget=2000.0,
            suggestions=[
                AllocationSuggestion("510300", "etf", 0.3, 0.2, 3000.0, "GREEN", False, False, ["正常"]),
                AllocationSuggestion("600519", "stock", 0.04, 0.05, 0.0, "YELLOW", True, True, ["暂停"]),
            ],
            manual_review_items=["600519: 暂停买入"],
            notes=["仅供人工确认"],
        )
        current_table = pd.DataFrame(
            {
                "symbol": ["510300", "600519"],
                "asset_type": ["etf", "stock"],
                "last_price": [3.8, 1600.0],
                "market_value": [3800.0, 1600.0],
                "current_weight": [0.32, 0.13],
                "target_weight": [0.30, 0.04],
                "weight_gap": [-0.02, -0.09],
            }
        )
        risk_table = pd.DataFrame(
            {
                "symbol": ["510300", "600519"],
                "asset_type": ["etf", "stock"],
                "status": ["GREEN", "YELLOW"],
                "reasons": ["正常", "暂停"],
            }
        )
        bundle = _make_bundle()

        monthly_paths = generator.save_monthly_report(
            recommendation=recommendation,
            current_table=current_table,
            risk_table=risk_table,
            data_bundle=bundle,
            config_summary={"monthly_budget": 10000.0},
            portfolio_cash=500.0,
        )
        assert monthly_paths["markdown"].exists()
        monthly_text = monthly_paths["markdown"].read_text(encoding="utf-8")
        assert "数据模式与来源" in monthly_text
        assert "当前组合快照" in monthly_text

        backtest_result = ExtendedBacktestResult(
            equity_curve=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-01", "2024-03-29"]),
                    "portfolio_value": [10000.0, 10200.0],
                    "cumulative_contribution": [10000.0, 10000.0],
                    "unit_nav": [1.0, 1.02],
                }
            ),
            trades=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-01"]),
                    "symbol": ["510300"],
                    "asset_type": ["etf"],
                    "status": ["GREEN"],
                    "total_cash_out": [3000.0],
                }
            ),
            monthly_records=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-01"]),
                    "month": ["2024-03"],
                    "actual_trade_day": ["2024-03-01"],
                }
            ),
            risk_records=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-29"]),
                    "symbol": ["600519"],
                    "asset_type": ["stock"],
                    "status": ["YELLOW"],
                    "reasons": ["暂停"],
                    "check_type": ["weekly_risk_check"],
                }
            ),
            metrics={"final_unit_nav": 1.02, "max_drawdown": 0.01},
            unfilled_orders=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-01"]),
                    "symbol": ["600519"],
                    "asset_type": ["stock"],
                    "recommended_amount": [2000.0],
                    "reason": ["paused_by_risk_rule"],
                }
            ),
            recommendation_records=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-01"]),
                    "symbol": ["510300"],
                    "asset_type": ["etf"],
                    "recommended_amount": [3000.0],
                    "pause_buy": [False],
                }
            ),
            portfolio_snapshots=pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-03-29"]),
                    "symbol": ["510300"],
                    "asset_type": ["etf"],
                    "market_value": [3800.0],
                    "current_weight": [0.32],
                    "target_weight": [0.30],
                    "weight_gap": [-0.02],
                    "total_value": [10200.0],
                    "cash": [6400.0],
                }
            ),
            metadata={"actual_monthly_trade_days": ["2024-03-01"], "actual_weekly_risk_days": ["2024-03-29"]},
        )

        backtest_paths = generator.save_backtest_report(
            result=backtest_result,
            data_bundle=bundle,
            config_summary={"monthly_budget": 10000.0},
        )
        assert backtest_paths["markdown"].exists()
        backtest_text = backtest_paths["markdown"].read_text(encoding="utf-8")
        assert "回测配置摘要" in backtest_text
        assert "结果限制说明" in backtest_text
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
