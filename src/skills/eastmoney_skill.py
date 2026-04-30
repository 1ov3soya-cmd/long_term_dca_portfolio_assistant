"""东财辅助 skill 占位实现。"""

from __future__ import annotations

import pandas as pd


class EastmoneySkill:
    """用于补充东财风格字段与视图的辅助模块。

    说明：
    - 本模块不是主行情 provider。
    - 主要用于未来补充东财风格字段映射、板块视图、资讯接口等辅助能力。
    """

    def normalize_symbol_view(self, symbol: str) -> dict[str, str]:
        """将代码整理为更贴近东财使用习惯的展示结构。"""

        normalized = str(symbol).zfill(6)
        market = "SH" if normalized.startswith(("5", "6")) else "SZ"
        return {
            "symbol": normalized,
            "eastmoney_code": f"{market}.{normalized}",
            "display_name": normalized,
        }

    def map_eastmoney_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        """补充常见东财字段别名。"""

        mapping = {
            "最新价": "latest_price",
            "涨跌幅": "pct_change",
            "主力净流入": "main_net_inflow",
        }
        return frame.rename(columns=mapping)

    def build_watchlist_view(self, frame: pd.DataFrame) -> pd.DataFrame:
        """生成更贴近东财观察习惯的标的视图。"""

        result = frame.copy()
        if "symbol" in result.columns:
            result["eastmoney_view"] = result["symbol"].apply(lambda item: self.normalize_symbol_view(str(item))["eastmoney_code"])
        return result

    # TODO: 未来可在此接入东财公告、新闻、资金流、板块热度等辅助能力。
    # TODO: 继续保持与主策略逻辑解耦，不替代主行情 provider。
