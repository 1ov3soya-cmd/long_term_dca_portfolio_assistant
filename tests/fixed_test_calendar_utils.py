from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.calendar_utils import (
    build_calendar_from_histories,
    first_trading_day_each_month,
    last_trading_day_each_month,
    last_trading_day_each_week,
    resolve_latest_trading_day,
)


def test_trading_calendar_derivation_and_rules() -> None:
    histories = {
        "510300": pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05", "2024-02-01"])}),
        "600519": pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-04", "2024-02-01"])}),
    }
    calendar = build_calendar_from_histories(histories, preferred_symbol="510300")

    assert calendar[0] == pd.Timestamp("2024-01-02")
    assert first_trading_day_each_month(calendar) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-02-01")]
    assert last_trading_day_each_month(calendar) == [pd.Timestamp("2024-01-05"), pd.Timestamp("2024-02-01")]
    assert last_trading_day_each_week(calendar) == [pd.Timestamp("2024-01-05"), pd.Timestamp("2024-02-01")]
    assert resolve_latest_trading_day(calendar, "2024-01-04") == pd.Timestamp("2024-01-03")
