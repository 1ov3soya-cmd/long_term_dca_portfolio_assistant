"""配置加载工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.exceptions import ConfigError


def load_yaml(path: str | Path) -> dict[str, Any]:
    """读取 YAML 配置。"""

    file_path = Path(path)
    json_fallback = file_path.with_suffix(".json")

    if file_path.exists():
        try:
            import yaml
        except ImportError:
            if not json_fallback.exists():
                raise ConfigError(
                    f"缺少 PyYAML，且未找到 JSON 回退配置: {json_fallback}"
                ) from None
            with json_fallback.open("r", encoding="utf-8") as file:
                data = json.load(file) or {}
        else:
            with file_path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
    elif json_fallback.exists():
        with json_fallback.open("r", encoding="utf-8") as file:
            data = json.load(file) or {}
    else:
        raise ConfigError(f"配置文件不存在: {file_path}")

    if not isinstance(data, dict):
        raise ConfigError(f"配置文件格式错误，需为映射结构: {file_path}")
    return data


def load_all_configs(config_dir: str | Path) -> dict[str, dict[str, Any]]:
    """批量读取目录下配置文件。"""

    base = Path(config_dir)
    return {
        "app": load_yaml(base / "app_config.yaml"),
        "portfolio": load_yaml(base / "portfolio_config.yaml"),
        "universe": load_yaml(base / "universe_config.yaml"),
        "risk": load_yaml(base / "risk_config.yaml"),
        "backtest": load_yaml(base / "backtest_config.yaml"),
        "sensitivity": load_yaml(base / "sensitivity_config.yaml"),
        "robustness": load_yaml(base / "robustness_config.yaml"),
        "archive": load_yaml(base / "archive_config.yaml"),
    }
