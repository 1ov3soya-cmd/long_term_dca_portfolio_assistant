"""Qlib 适配器占位。

第一版策略不把主流程绑定在 Qlib 上。
若后续需要引入 Qlib，可在本模块内实现数据转换、回测调用与指标映射。
"""

from __future__ import annotations

from src.utils.exceptions import BacktestError


class QlibAdapter:
    """Qlib 适配器占位实现。"""

    def __init__(self) -> None:
        self.enabled = False

    def run_backtest(self) -> None:
        """占位接口。

        当前版本优先使用自研低频 MVP 回测器。
        """

        raise BacktestError("当前版本未启用 Qlib 深度接入，请使用 MVP 回测器。")
