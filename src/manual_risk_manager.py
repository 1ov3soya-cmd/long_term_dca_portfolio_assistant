"""人工逻辑红线配置读取与校验。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.config_loader import load_yaml


TRUE_SET = {True, 1, "1", "true", "yes", "y", "on"}


@dataclass(slots=True)
class ManualRiskFlag:
    """单个标的的人工逻辑红线状态。"""

    symbol: str
    asset_type: str
    effective_from: str
    manual_pause_buy: bool = False
    manual_force_review: bool = False
    thesis_broken: bool = False
    note: str = ""
    updated_at: str = ""
    updated_by: str = ""

    def is_active(self, as_of_date: str | pd.Timestamp) -> bool:
        return pd.Timestamp(as_of_date) >= pd.Timestamp(self.effective_from)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "asset_type": self.asset_type,
            "effective_from": self.effective_from,
            "manual_pause_buy": self.manual_pause_buy,
            "manual_force_review": self.manual_force_review,
            "thesis_broken": self.thesis_broken,
            "note": self.note,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


class ManualRiskFlagManager:
    """负责读取、校验并按日期生效人工逻辑红线。"""

    def __init__(self, flag_path: str | Path | None = None, thesis_flag_path: str | Path | None = None) -> None:
        self.flag_path = Path(flag_path) if flag_path else None
        self.thesis_flag_path = Path(thesis_flag_path) if thesis_flag_path else None

    def load_active_flags(self, as_of_date: str | pd.Timestamp) -> dict[str, ManualRiskFlag]:
        """读取当前生效的人工逻辑红线。"""

        flags = self.load_all_flags()
        return {symbol: flag for symbol, flag in flags.items() if flag.is_active(as_of_date)}

    def load_all_flags(self) -> dict[str, ManualRiskFlag]:
        """读取全部人工逻辑红线，并兼容旧 thesis_broken CSV。"""

        flags: dict[str, ManualRiskFlag] = {}
        if self.flag_path and self.flag_path.exists():
            payload = load_yaml(self.flag_path)
            symbols = payload.get("manual_risk_flags", {}).get("symbols", {})
            for symbol, raw in symbols.items():
                normalized_symbol = str(symbol).zfill(6)
                flags[normalized_symbol] = ManualRiskFlag(
                    symbol=normalized_symbol,
                    asset_type=str(raw.get("asset_type", "")).lower() or "unknown",
                    effective_from=str(raw.get("effective_from", "1900-01-01")),
                    manual_pause_buy=self._to_bool(raw.get("manual_pause_buy", False)),
                    manual_force_review=self._to_bool(raw.get("manual_force_review", False)),
                    thesis_broken=self._to_bool(raw.get("thesis_broken", False)),
                    note=str(raw.get("note", "")),
                    updated_at=str(raw.get("updated_at", "")),
                    updated_by=str(raw.get("updated_by", "")),
                )

        if self.thesis_flag_path and self.thesis_flag_path.exists():
            frame = pd.read_csv(self.thesis_flag_path)
            if not frame.empty and "symbol" in frame.columns and "thesis_broken" in frame.columns:
                for _, row in frame.iterrows():
                    symbol = str(row["symbol"]).zfill(6)
                    thesis_broken = self._to_bool(row["thesis_broken"])
                    if not thesis_broken:
                        continue
                    existing = flags.get(symbol)
                    if existing is None:
                        flags[symbol] = ManualRiskFlag(
                            symbol=symbol,
                            asset_type="unknown",
                            effective_from="1900-01-01",
                            thesis_broken=True,
                            note=str(row.get("reason", "legacy_thesis_flag")),
                            updated_at=str(row.get("last_update", "")),
                            updated_by="legacy_csv",
                        )
                    else:
                        existing.thesis_broken = True
                        if not existing.note:
                            existing.note = str(row.get("reason", "legacy_thesis_flag"))
        return flags

    def validate(self, target_table: pd.DataFrame) -> dict[str, Any]:
        """校验人工逻辑红线配置结构。"""

        issues: list[dict[str, Any]] = []
        allowed_symbols = set(target_table["symbol"].astype(str).tolist()) if not target_table.empty else set()
        flags = self.load_all_flags()
        raw_symbols = {}
        if self.flag_path and self.flag_path.exists():
            raw_payload = load_yaml(self.flag_path)
            raw_symbols = raw_payload.get("manual_risk_flags", {}).get("symbols", {})
        if not flags:
            issues.append({"symbol": "", "level": "warning", "message": "未读取到人工逻辑红线配置，当前视为全部关闭。"})

        for symbol, flag in flags.items():
            if allowed_symbols and symbol not in allowed_symbols:
                issues.append({"symbol": symbol, "level": "error", "message": "symbol 不在当前资产池内"})
            try:
                pd.Timestamp(flag.effective_from)
            except Exception:  # noqa: BLE001
                issues.append({"symbol": symbol, "level": "error", "message": "effective_from 日期格式非法"})
            raw = raw_symbols.get(symbol, raw_symbols.get(str(int(symbol)) if symbol.isdigit() else symbol, {}))
            for field_name in ["manual_pause_buy", "manual_force_review", "thesis_broken"]:
                raw_value = raw.get(field_name, False) if isinstance(raw, dict) else False
                if not self._is_valid_bool_value(raw_value):
                    issues.append({"symbol": symbol, "level": "error", "message": f"{field_name} 不是合法布尔值"})

        issue_frame = pd.DataFrame(issues)
        flag_frame = pd.DataFrame([flag.to_dict() for flag in flags.values()])
        return {
            "issues": issue_frame,
            "flags": flag_frame,
            "valid": issue_frame.loc[issue_frame["level"] == "error"].empty if not issue_frame.empty else True,
        }

    @staticmethod
    def _to_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in {str(item).lower() for item in TRUE_SET}

    @staticmethod
    def _is_valid_bool_value(value: object) -> bool:
        if isinstance(value, bool):
            return True
        return str(value).strip().lower() in {"0", "1", "true", "false", "yes", "no", "y", "n", "on", "off"}
