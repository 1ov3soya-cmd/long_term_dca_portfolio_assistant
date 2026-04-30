from pathlib import Path
import shutil
import sys
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cache import DataCache


def test_data_cache_save_load_merge_fixed() -> None:
    temp_dir = PROJECT_ROOT / "data" / "processed" / f"cache_test_{uuid.uuid4().hex}"
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        cache = DataCache(temp_dir, cache_format="csv")
        base = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "symbol": ["510300", "510300"],
                "close": [1.0, 1.1],
            }
        )
        incoming = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "symbol": ["510300", "510300"],
                "close": [1.15, 1.2],
            }
        )

        cache.save("510300", "etf", base)
        loaded = cache.load("510300", "etf")
        merged = cache.merge(loaded, incoming)

        assert len(loaded) == 2
        assert len(merged) == 3
        assert merged["close"].iloc[-1] == 1.2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
