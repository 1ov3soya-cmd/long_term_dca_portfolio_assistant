from pathlib import Path
import shutil
import sys
import uuid

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cache import DataCache
from src.data_loader import MarketDataLoader
from src.utils.exceptions import DataProviderError


class FakeProvider:
    name = "fake"
    source_api = "fake_api"
    adjustment_mode = "forward"

    def __init__(self, frame: pd.DataFrame | None = None, error: Exception | None = None) -> None:
        self.frame = frame if frame is not None else pd.DataFrame()
        self.error = error

    def fetch_history(self, symbol: str, asset_type: str, start_date: str, end_date: str) -> pd.DataFrame:
        if self.error is not None:
            raise self.error
        return self.frame.copy()


def test_loader_falls_back_to_cache_when_provider_fails() -> None:
    temp_root = PROJECT_ROOT / "data" / "processed" / f"loader_test_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        loader = MarketDataLoader(PROJECT_ROOT)
        loader.cache = DataCache(temp_root, cache_format="csv")
        cached = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "symbol": ["600519", "600519"],
                "asset_type": ["stock", "stock"],
                "open": [1.0, 1.1],
                "high": [1.1, 1.2],
                "low": [0.9, 1.0],
                "close": [1.05, 1.15],
            }
        )
        loader.cache.save("600519", "stock", cached, variant="forward")
        loader.provider = FakeProvider(error=DataProviderError("network down"))

        frame = loader.load_symbol_history("600519", "stock", "2024-01-02", "2024-01-03", use_incremental=True)

        assert len(frame) == 2
        assert frame["close"].iloc[-1] == 1.15
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
