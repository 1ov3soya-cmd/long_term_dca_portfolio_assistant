"""运行结果归档与快照输出。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any

from src.utils.config_loader import load_yaml
from src.utils.logger import get_logger


class RunArchiver:
    """为关键命令生成运行级归档目录。"""

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        self.settings = configs.get("archive", {}).get("archive", {})
        log_level = configs.get("app", {}).get("runtime", {}).get("log_level", "INFO")
        self.logger = get_logger(self.__class__.__name__, log_level)
        archive_root_dir = self.settings.get("archive_root_dir", "reports/runs")
        self.archive_root = self.project_root / archive_root_dir

    def start_run(self, command_name: str) -> dict[str, Any] | None:
        """初始化本次运行的归档上下文。"""

        if not bool(self.settings.get("archive_enabled", True)):
            return None

        started_at = datetime.now()
        run_id = f"{started_at:%Y%m%d_%H%M%S}_{command_name.replace('-', '_')}"
        run_dir = self.archive_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return {"run_id": run_id, "run_dir": run_dir, "started_at": started_at, "command_name": command_name}

    def build_effective_config_snapshot(self) -> dict[str, Any]:
        """构建实际生效的配置快照。"""

        snapshot = {
            "app": deepcopy(self.configs.get("app", {})),
            "portfolio": deepcopy(self.configs.get("portfolio", {})),
            "universe": deepcopy(self.configs.get("universe", {})),
            "risk": deepcopy(self.configs.get("risk", {})),
            "backtest": deepcopy(self.configs.get("backtest", {})),
            "sensitivity": deepcopy(self.configs.get("sensitivity", {})),
            "robustness": deepcopy(self.configs.get("robustness", {})),
            "archive": deepcopy(self.configs.get("archive", {})),
        }
        if bool(self.settings.get("archive_include_manual_risk_snapshot", True)):
            manual_path = self._resolve_manual_risk_path()
            snapshot["manual_risk_file_path"] = str(manual_path) if manual_path else ""
            snapshot["manual_risk_flags_snapshot"] = self._load_optional_snapshot(manual_path)
        return snapshot

    def finalize(
        self,
        run_context: dict[str, Any] | None,
        cli_args: dict[str, Any],
        effective_config_snapshot: dict[str, Any],
        output_artifacts: dict[str, Any],
        key_summary: dict[str, Any],
        notes: list[str],
        status: str,
        runtime_meta: dict[str, Any],
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> dict[str, Path]:
        """落盘运行归档文件。"""

        if run_context is None:
            return {}

        warnings = warnings or []
        errors = errors or []
        finished_at = datetime.now()
        started_at = run_context["started_at"]
        duration_seconds = round((finished_at - started_at).total_seconds(), 3)
        run_dir = run_context["run_dir"]

        manifest = {
            "run_id": run_context["run_id"],
            "command_name": run_context["command_name"],
            "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": duration_seconds,
            "status": status,
            "end_date": runtime_meta.get("end_date"),
            "data_mode": runtime_meta.get("data_mode", ""),
            "provider_name": runtime_meta.get("provider_name", ""),
            "adj_mode": runtime_meta.get("adj_mode", ""),
            "manual_risk_file": runtime_meta.get("manual_risk_file", ""),
            "code_version_hint": self._code_version_hint(),
            "warnings_count": len(warnings),
            "errors_count": len(errors),
        }

        paths = {
            "run_manifest": run_dir / "run_manifest.json",
            "effective_config_snapshot": run_dir / "effective_config_snapshot.json",
            "cli_args": run_dir / "cli_args.json",
            "output_artifacts": run_dir / "output_artifacts.json",
            "key_summary": run_dir / "key_summary.json",
            "notes": run_dir / "notes.md",
        }

        self._write_json(paths["run_manifest"], manifest)
        self._write_json(paths["effective_config_snapshot"], effective_config_snapshot)
        self._write_json(paths["cli_args"], cli_args)
        self._write_json(paths["output_artifacts"], self._normalize_artifacts(output_artifacts))
        self._write_json(paths["key_summary"], key_summary)
        paths["notes"].write_text(
            self._render_notes(
                manifest=manifest,
                output_artifacts=output_artifacts,
                key_summary=key_summary,
                notes=notes,
                warnings=warnings,
                errors=errors,
            ),
            encoding="utf-8",
        )

        if bool(self.settings.get("update_latest_index", True)):
            self._update_latest_index(run_context["command_name"], manifest["run_id"], run_dir, manifest["status"], manifest["finished_at"])

        self.logger.info("运行归档已输出: %s", run_dir)
        return paths

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _resolve_manual_risk_path(self) -> Path | None:
        manual_path = self.configs.get("universe", {}).get("manual_flags", {}).get("logic_risk_flag_file")
        if not manual_path:
            return None
        path = Path(manual_path)
        return path if path.is_absolute() else self.project_root / path

    @staticmethod
    def _normalize_artifacts(output_artifacts: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in output_artifacts.items():
            if isinstance(value, dict):
                normalized[key] = {sub_key: str(sub_value) for sub_key, sub_value in value.items()}
            elif isinstance(value, list):
                normalized[key] = [str(item) for item in value]
            else:
                normalized[key] = str(value)
        return normalized

    def _load_optional_snapshot(self, path: Path | None) -> dict[str, Any]:
        if path is None or not path.exists():
            return {}
        try:
            return load_yaml(path)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("人工逻辑红线快照读取失败: %s", exc)
            return {"load_error": str(exc), "path": str(path)}

    def _code_version_hint(self) -> str:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:  # noqa: BLE001
            return ""
        return completed.stdout.strip() if completed.returncode == 0 else ""

    def _update_latest_index(self, command_name: str, run_id: str, run_dir: Path, status: str, finished_at: str) -> None:
        latest_index_path = self.archive_root / "latest_index.json"
        if latest_index_path.exists():
            try:
                payload = json.loads(latest_index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
        else:
            payload = {}
        payload[command_name] = {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "status": status,
            "finished_at": finished_at,
        }
        self._write_json(latest_index_path, payload)

    @staticmethod
    def _render_notes(
        manifest: dict[str, Any],
        output_artifacts: dict[str, Any],
        key_summary: dict[str, Any],
        notes: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> str:
        lines = [
            "# 运行说明",
            "",
            f"- command_name: {manifest['command_name']}",
            f"- run_id: {manifest['run_id']}",
            f"- status: {manifest['status']}",
            f"- started_at: {manifest['started_at']}",
            f"- finished_at: {manifest['finished_at']}",
            f"- duration_seconds: {manifest['duration_seconds']}",
            "",
            "## 本次运行做了什么",
            f"- 已执行 `{manifest['command_name']}` 命令，并记录本次运行的配置快照、输入参数、输出产物索引与关键摘要。",
            "",
            "## 关键告警",
        ]
        if warnings:
            lines.extend([f"- {warning}" for warning in warnings])
        else:
            lines.append("- 当前无关键告警。")

        lines.extend(["", "## 失败或限制"])
        if errors:
            lines.extend([f"- {error}" for error in errors])
        else:
            lines.append("- 当前无失败信息。")

        if notes:
            lines.extend(["", "## 额外说明"])
            lines.extend([f"- {note}" for note in notes])

        if key_summary:
            lines.extend(["", "## 关键摘要"])
            for key, value in key_summary.items():
                lines.append(f"- {key}: {value}")

        lines.extend(["", "## 建议优先查看的输出文件"])
        if output_artifacts:
            normalized = RunArchiver._normalize_artifacts(output_artifacts)
            for key, value in normalized.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- 当前无输出产物记录。")
        return "\n".join(lines) + "\n"
