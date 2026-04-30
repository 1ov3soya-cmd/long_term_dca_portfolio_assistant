"""组合与持仓状态管理。"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.schemas import Holding


def build_target_table(portfolio_config: dict[str, Any]) -> pd.DataFrame:
    """从配置构建目标权重表。"""

    records: list[dict[str, Any]] = []
    for item in portfolio_config["etf_pool"]:
        records.append(
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "asset_type": "etf",
                "category": item.get("category", ""),
                "target_weight": float(item["target_weight"]),
            }
        )
    for item in portfolio_config["stock_pool"]:
        records.append(
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "asset_type": "stock",
                "category": item.get("category", ""),
                "target_weight": float(item["target_weight"]),
            }
        )
    return pd.DataFrame(records)


class PortfolioState:
    """组合状态。

    设计约束：
    - 第一版只支持买入增持，不自动卖出。
    - 卖出逻辑未来仅在“人工确认 + 明确触发条件”下扩展，避免本项目被误用为自动止损系统。
    """

    def __init__(self, holdings: list[Holding] | None = None, cash: float = 0.0) -> None:
        self.positions: dict[str, Holding] = {item.symbol: item for item in holdings or []}
        self.cash = float(cash)

    @classmethod
    def from_csv(cls, file_path: str | Path, initial_cash: float = 0.0) -> "PortfolioState":
        """从手工持仓文件加载组合状态。"""

        path = Path(file_path)
        if not path.exists():
            return cls(cash=initial_cash)

        frame = pd.read_csv(path)
        if frame.empty:
            return cls(cash=initial_cash)

        holdings = [
            Holding(
                symbol=str(row["symbol"]).zfill(6),
                asset_type=str(row["asset_type"]),
                quantity=int(row["quantity"]),
                avg_cost=float(row["avg_cost"]),
            )
            for _, row in frame.iterrows()
            if int(row.get("quantity", 0)) > 0
        ]
        return cls(holdings=holdings, cash=initial_cash)

    def to_frame(self, latest_prices: dict[str, float], target_table: pd.DataFrame | None = None) -> pd.DataFrame:
        """导出当前持仓明细。"""

        records: list[dict[str, Any]] = []
        total_value = self.total_value(latest_prices)

        for holding in self.positions.values():
            last_price = float(latest_prices.get(holding.symbol, 0.0))
            market_value = holding.quantity * last_price
            current_weight = market_value / total_value if total_value > 0 else 0.0
            records.append(
                {
                    "symbol": holding.symbol,
                    "asset_type": holding.asset_type,
                    "quantity": holding.quantity,
                    "avg_cost": holding.avg_cost,
                    "last_price": last_price,
                    "market_value": market_value,
                    "current_weight": current_weight,
                }
            )

        frame = pd.DataFrame(records)
        if frame.empty:
            frame = pd.DataFrame(
                columns=[
                    "symbol",
                    "asset_type",
                    "quantity",
                    "avg_cost",
                    "last_price",
                    "market_value",
                    "current_weight",
                ]
            )
        if target_table is not None:
            frame = target_table.merge(frame, on=["symbol", "asset_type"], how="left")
            frame["quantity"] = frame["quantity"].fillna(0).astype(int)
            frame["avg_cost"] = frame["avg_cost"].fillna(0.0)
            frame["last_price"] = frame["last_price"].fillna(0.0)
            frame["market_value"] = frame["market_value"].fillna(0.0)
            frame["current_weight"] = frame["current_weight"].fillna(0.0)
            frame["weight_gap"] = frame["target_weight"] - frame["current_weight"]
        return frame.sort_values(["asset_type", "symbol"]).reset_index(drop=True)

    def market_value(self, latest_prices: dict[str, float]) -> float:
        """返回持仓市值。"""

        return float(
            sum(holding.quantity * float(latest_prices.get(holding.symbol, 0.0)) for holding in self.positions.values())
        )

    def total_value(self, latest_prices: dict[str, float]) -> float:
        """返回组合总资产。"""

        return self.cash + self.market_value(latest_prices)

    def get_holding(self, symbol: str) -> Holding | None:
        """获取单个持仓。"""

        return self.positions.get(symbol)

    def apply_buy(self, symbol: str, asset_type: str, quantity: int, total_cash_out: float) -> None:
        """应用买入成交结果。"""

        if quantity <= 0:
            return

        self.cash -= total_cash_out
        unit_cost = total_cash_out / quantity

        current = self.positions.get(symbol)
        if current is None:
            self.positions[symbol] = Holding(symbol=symbol, asset_type=asset_type, quantity=quantity, avg_cost=unit_cost)
            return

        total_qty = current.quantity + quantity
        weighted_cost = (current.avg_cost * current.quantity + unit_cost * quantity) / total_qty
        self.positions[symbol] = Holding(
            symbol=symbol,
            asset_type=asset_type,
            quantity=total_qty,
            avg_cost=weighted_cost,
        )

    def add_cash(self, amount: float) -> None:
        """增加现金。"""

        self.cash += amount

    def export_holdings(self, file_path: str | Path) -> None:
        """导出持仓到 CSV。"""

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame([asdict(value) for value in self.positions.values()])
        if frame.empty:
            frame = pd.DataFrame(columns=["symbol", "asset_type", "quantity", "avg_cost"])
        frame["last_update"] = pd.Timestamp.now().strftime("%Y-%m-%d")
        frame.to_csv(path, index=False, encoding="utf-8-sig")
