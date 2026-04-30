"""运行结果对比器。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logger import get_logger


@dataclass(slots=True)
class ArchivedRunRecord:
    """单次归档运行的读取结果。"""

    run_ref: str
    run_dir: Path
    manifest: dict[str, Any]
    cli_args: dict[str, Any]
    config_snapshot: dict[str, Any]
    output_artifacts: dict[str, Any]
    key_summary: dict[str, Any]
    notes_text: str
    missing_files: list[str]


class RunCompareEngine:
    """比较两次已归档运行，并输出结构化差异报告。"""

    REQUIRED_FILES = {
        "run_manifest": "run_manifest.json",
        "cli_args": "cli_args.json",
        "config_snapshot": "effective_config_snapshot.json",
        "output_artifacts": "output_artifacts.json",
        "key_summary": "key_summary.json",
        "notes": "notes.md",
    }
    CRITICAL_FILES = {"run_manifest", "key_summary"}
    MAJOR_CONFIG_PREFIXES = [
        "app.efinance.adjustment_mode",
        "app.schedule.monthly_invest_day_rule",
        "risk.",
        "backtest.backtest.execution_rule",
        "backtest.transaction_cost",
        "manual_risk_file_path",
        "manual_risk_flags_snapshot",
    ]
    MANIFEST_COMPARE_KEYS = [
        "command_name",
        "status",
        "started_at",
        "finished_at",
        "duration_seconds",
        "end_date",
        "data_mode",
        "provider_name",
        "adj_mode",
        "manual_risk_file",
        "warnings_count",
        "errors_count",
    ]

    def __init__(self, project_root: str | Path, log_level: str = "INFO") -> None:
        self.project_root = Path(project_root)
        self.runs_root = self.project_root / "reports" / "runs"
        self.compare_root = self.project_root / "reports" / "run_compare"
        self.logger = get_logger(self.__class__.__name__, log_level)

    def compare_runs(
        self,
        run_a: str | None = None,
        run_b: str | None = None,
        latest_command: str | None = None,
        brief: bool = False,
    ) -> dict[str, Any]:
        """比较两次归档运行，并落盘对比结果。"""

        if latest_command:
            run_a, run_b = self._resolve_latest_pair(latest_command)
        if not run_a or not run_b:
            raise ValueError("compare-runs 需要同时提供 --run-a 和 --run-b，或使用 --latest <command>。")

        record_a = self._load_run_record(run_a)
        record_b = self._load_run_record(run_b)
        compared_at = datetime.now()
        compare_id = self._build_compare_id(compared_at, record_a.run_dir.name, record_b.run_dir.name)
        compare_dir = self.compare_root / compare_id
        compare_dir.mkdir(parents=True, exist_ok=True)

        manifest_diff = self._compare_scalar_fields(
            record_a.manifest,
            record_b.manifest,
            self.MANIFEST_COMPARE_KEYS,
        )
        cli_diff = self._compare_mapping(
            self._flatten_mapping(record_a.cli_args),
            self._flatten_mapping(record_b.cli_args),
        )
        config_diff = self._compare_mapping(
            self._flatten_mapping(record_a.config_snapshot),
            self._flatten_mapping(record_b.config_snapshot),
        )
        artifact_diff = self._compare_mapping(
            self._flatten_mapping(record_a.output_artifacts),
            self._flatten_mapping(record_b.output_artifacts),
        )
        summary_diff_df = self._build_summary_diff(record_a.key_summary, record_b.key_summary)
        notes_diff = self._compare_notes(record_a.notes_text, record_b.notes_text)
        comparability = self._assess_comparability(record_a, record_b, config_diff)
        top_config_changes = self._top_config_changes(config_diff)
        top_summary_changes = self._top_summary_changes(summary_diff_df)
        top_attention_points = self._build_attention_points(
            comparability=comparability,
            top_config_changes=top_config_changes,
            top_summary_changes=top_summary_changes,
            artifact_diff=artifact_diff,
        )
        compare_status = self._compare_status(record_a, record_b)

        compare_manifest = {
            "compare_id": compare_id,
            "run_a": {"run_ref": record_a.run_ref, "run_dir": str(record_a.run_dir)},
            "run_b": {"run_ref": record_b.run_ref, "run_dir": str(record_b.run_dir)},
            "compared_at": compared_at.strftime("%Y-%m-%d %H:%M:%S"),
            "compare_status": compare_status,
            "comparable_level": comparability["level"],
            "command_match": bool(record_a.manifest.get("command_name") == record_b.manifest.get("command_name")),
            "end_date_match": bool(record_a.manifest.get("end_date") == record_b.manifest.get("end_date")),
            "key_findings_count": len(top_attention_points),
        }

        compare_summary = {
            "top_config_changes": top_config_changes,
            "top_summary_changes": top_summary_changes,
            "manual_risk_changed": self._has_changed_path(config_diff, "manual_risk_file_path")
            or self._has_changed_path(config_diff, "manual_risk_flags_snapshot"),
            "adj_mode_changed": bool(record_a.manifest.get("adj_mode") != record_b.manifest.get("adj_mode"))
            or self._has_changed_path(config_diff, "app.efinance.adjustment_mode"),
            "data_mode_changed": bool(record_a.manifest.get("data_mode") != record_b.manifest.get("data_mode"))
            or self._has_changed_path(config_diff, "app.runtime.data_mode"),
            "comparability_assessment": comparability,
            "top_attention_points": top_attention_points,
            "missing_files": {
                "run_a": record_a.missing_files,
                "run_b": record_b.missing_files,
            },
        }

        config_diff_payload = {
            "run_a": {"run_ref": record_a.run_ref, "run_dir": str(record_a.run_dir)},
            "run_b": {"run_ref": record_b.run_ref, "run_dir": str(record_b.run_dir)},
            "cli_args_diff": cli_diff,
            "config_snapshot_diff": config_diff,
            "artifact_diff": artifact_diff,
            "notes_diff": notes_diff,
            "manifest_diff": manifest_diff,
        }

        summary_diff_path = compare_dir / "summary_diff.csv"
        summary_diff_df.to_csv(summary_diff_path, index=False, encoding="utf-8-sig")

        compare_manifest_path = compare_dir / "compare_manifest.json"
        compare_summary_path = compare_dir / "compare_summary.json"
        compare_report_path = compare_dir / "compare_report.md"
        config_diff_path = compare_dir / "config_diff.json"

        sanitized_manifest = self._sanitize_for_json(compare_manifest)
        sanitized_summary = self._sanitize_for_json(compare_summary)
        sanitized_config_diff = self._sanitize_for_json(config_diff_payload)

        compare_manifest_path.write_text(json.dumps(sanitized_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        compare_summary_path.write_text(json.dumps(sanitized_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        config_diff_path.write_text(json.dumps(sanitized_config_diff, ensure_ascii=False, indent=2), encoding="utf-8")
        compare_report_path.write_text(
            self._render_compare_report(
                record_a=record_a,
                record_b=record_b,
                compare_manifest=sanitized_manifest,
                compare_summary=sanitized_summary,
                manifest_diff=manifest_diff,
                cli_diff=cli_diff,
                config_diff=config_diff,
                artifact_diff=artifact_diff,
                notes_diff=notes_diff,
                summary_diff_df=summary_diff_df,
                brief=brief,
            ),
            encoding="utf-8",
        )

        self._update_latest_compare_index(compare_id, compare_dir, compare_manifest)

        self.logger.info("运行对比报告已输出: %s", compare_report_path)
        return {
            "compare_manifest": sanitized_manifest,
            "compare_summary": sanitized_summary,
            "paths": {
                "compare_manifest": compare_manifest_path,
                "compare_summary": compare_summary_path,
                "compare_report": compare_report_path,
                "config_diff": config_diff_path,
                "summary_diff": summary_diff_path,
            },
        }

    def _resolve_latest_pair(self, command_name: str) -> tuple[str, str]:
        """解析某类命令最近两次运行。"""

        if not self.runs_root.exists():
            raise FileNotFoundError(f"归档目录不存在: {self.runs_root}")
        matched_records: list[tuple[str, Path]] = []
        for run_dir in sorted([item for item in self.runs_root.iterdir() if item.is_dir()], key=lambda item: item.name):
            manifest_path = run_dir / "run_manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if manifest.get("command_name") == command_name:
                matched_records.append((run_dir.name, run_dir))
        if len(matched_records) < 2:
            raise ValueError(f"归档中少于两次 `{command_name}` 运行，无法使用 --latest 比较。")
        return matched_records[-2][0], matched_records[-1][0]

    def _load_run_record(self, run_ref: str) -> ArchivedRunRecord:
        """读取单次归档运行。"""

        run_dir = self._resolve_run_dir(run_ref)
        missing_files: list[str] = []
        manifest = self._load_json_or_default(run_dir / self.REQUIRED_FILES["run_manifest"], {}, missing_files, "run_manifest")
        cli_args = self._load_json_or_default(run_dir / self.REQUIRED_FILES["cli_args"], {}, missing_files, "cli_args")
        config_snapshot = self._load_json_or_default(
            run_dir / self.REQUIRED_FILES["config_snapshot"],
            {},
            missing_files,
            "config_snapshot",
        )
        output_artifacts = self._load_json_or_default(
            run_dir / self.REQUIRED_FILES["output_artifacts"],
            {},
            missing_files,
            "output_artifacts",
        )
        key_summary = self._load_json_or_default(run_dir / self.REQUIRED_FILES["key_summary"], {}, missing_files, "key_summary")
        notes_path = run_dir / self.REQUIRED_FILES["notes"]
        if notes_path.exists():
            notes_text = notes_path.read_text(encoding="utf-8")
        else:
            notes_text = ""
            missing_files.append("notes")
        return ArchivedRunRecord(
            run_ref=run_ref,
            run_dir=run_dir,
            manifest=manifest,
            cli_args=cli_args,
            config_snapshot=config_snapshot,
            output_artifacts=output_artifacts,
            key_summary=key_summary,
            notes_text=notes_text,
            missing_files=missing_files,
        )

    def _resolve_run_dir(self, run_ref: str) -> Path:
        """根据 run_id 或目录路径解析运行目录。"""

        candidate = Path(run_ref)
        if candidate.exists():
            return candidate
        run_dir = self.runs_root / run_ref
        if run_dir.exists():
            return run_dir
        raise FileNotFoundError(f"未找到运行归档目录: {run_ref}")

    @staticmethod
    def _load_json_or_default(
        path: Path,
        default: dict[str, Any],
        missing_files: list[str],
        missing_label: str,
    ) -> dict[str, Any]:
        """读取 JSON，缺失或损坏时回退到默认值。"""

        if not path.exists():
            missing_files.append(missing_label)
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            missing_files.append(f"{missing_label}:invalid_json")
            return default

    @staticmethod
    def _build_compare_id(compared_at: datetime, run_a_name: str, run_b_name: str) -> str:
        """构建比较目录 ID。"""

        return f"{compared_at:%Y%m%d_%H%M%S_%f}_{run_a_name}_vs_{run_b_name}"

    @staticmethod
    def _flatten_mapping(data: Any, prefix: str = "") -> dict[str, Any]:
        """将嵌套 JSON 结构拍平为 path -> value。"""

        items: dict[str, Any] = {}
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else str(key)
                items.update(RunCompareEngine._flatten_mapping(value, new_prefix))
            return items
        if isinstance(data, list):
            for index, value in enumerate(data):
                new_prefix = f"{prefix}[{index}]"
                items.update(RunCompareEngine._flatten_mapping(value, new_prefix))
            return items
        items[prefix or "$"] = data
        return items

    @staticmethod
    def _compare_scalar_fields(
        data_a: dict[str, Any],
        data_b: dict[str, Any],
        keys: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """比较固定键列表。"""

        same_items: list[dict[str, Any]] = []
        changed_items: list[dict[str, Any]] = []
        only_a_items: list[dict[str, Any]] = []
        only_b_items: list[dict[str, Any]] = []
        for key in keys:
            in_a = key in data_a
            in_b = key in data_b
            if in_a and in_b:
                if data_a[key] == data_b[key]:
                    same_items.append({"key": key, "value": data_a[key]})
                else:
                    changed_items.append({"key": key, "value_a": data_a[key], "value_b": data_b[key]})
            elif in_a:
                only_a_items.append({"key": key, "value": data_a[key]})
            elif in_b:
                only_b_items.append({"key": key, "value": data_b[key]})
        return {
            "same_items": same_items,
            "changed_items": changed_items,
            "only_a_items": only_a_items,
            "only_b_items": only_b_items,
        }

    @staticmethod
    def _compare_mapping(
        flat_a: dict[str, Any],
        flat_b: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        """比较拍平后的映射。"""

        keys = sorted(set(flat_a) | set(flat_b))
        added_keys: list[dict[str, Any]] = []
        removed_keys: list[dict[str, Any]] = []
        changed_values: list[dict[str, Any]] = []
        same_keys: list[dict[str, Any]] = []
        for key in keys:
            in_a = key in flat_a
            in_b = key in flat_b
            if in_a and in_b:
                if flat_a[key] == flat_b[key]:
                    same_keys.append({"path": key, "value": flat_a[key]})
                else:
                    changed_values.append({"path": key, "value_a": flat_a[key], "value_b": flat_b[key]})
            elif in_a:
                removed_keys.append({"path": key, "value_a": flat_a[key]})
            elif in_b:
                added_keys.append({"path": key, "value_b": flat_b[key]})
        return {
            "added_keys": added_keys,
            "removed_keys": removed_keys,
            "changed_values": changed_values,
            "same_keys": same_keys,
        }

    @staticmethod
    def _build_summary_diff(summary_a: dict[str, Any], summary_b: dict[str, Any]) -> pd.DataFrame:
        """比较 key_summary，并对数值字段计算变化。"""

        keys = sorted(set(summary_a) | set(summary_b))
        rows: list[dict[str, Any]] = []
        for key in keys:
            in_a = key in summary_a
            in_b = key in summary_b
            value_a = summary_a.get(key)
            value_b = summary_b.get(key)
            row: dict[str, Any] = {
                "key": key,
                "value_a": value_a,
                "value_b": value_b,
                "change_type": "same",
                "absolute_change": "",
                "relative_change": "",
                "direction": "unchanged",
            }
            if in_a and in_b:
                if value_a != value_b:
                    row["change_type"] = "changed"
                if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
                    absolute_change = float(value_b) - float(value_a)
                    row["absolute_change"] = absolute_change
                    if float(value_a) != 0:
                        row["relative_change"] = absolute_change / float(value_a)
                    row["direction"] = "up" if absolute_change > 0 else "down" if absolute_change < 0 else "unchanged"
            elif in_a:
                row["change_type"] = "removed"
                row["direction"] = "removed"
            else:
                row["change_type"] = "added"
                row["direction"] = "added"
            rows.append(row)
        return pd.DataFrame(rows)

    @staticmethod
    def _compare_notes(notes_a: str, notes_b: str) -> dict[str, Any]:
        """比较 notes.md 的关键告警与限制摘要。"""

        sections_a = RunCompareEngine._extract_notes_sections(notes_a)
        sections_b = RunCompareEngine._extract_notes_sections(notes_b)
        return {
            "warnings": RunCompareEngine._compare_string_lists(
                sections_a.get("warnings", []),
                sections_b.get("warnings", []),
            ),
            "limitations": RunCompareEngine._compare_string_lists(
                sections_a.get("limitations", []),
                sections_b.get("limitations", []),
            ),
            "extra_notes": RunCompareEngine._compare_string_lists(
                sections_a.get("extra_notes", []),
                sections_b.get("extra_notes", []),
            ),
        }

    @staticmethod
    def _extract_notes_sections(notes_text: str) -> dict[str, list[str]]:
        """从 notes.md 提取关键告警、限制与额外说明。"""

        section_map = {
            "## 关键告警": "warnings",
            "## 失败或限制": "limitations",
            "## 额外说明": "extra_notes",
        }
        current_section = ""
        extracted = {"warnings": [], "limitations": [], "extra_notes": []}
        for raw_line in notes_text.splitlines():
            line = raw_line.strip()
            if line in section_map:
                current_section = section_map[line]
                continue
            if line.startswith("## "):
                current_section = ""
                continue
            if current_section and line.startswith("- "):
                extracted[current_section].append(line[2:].strip())
        return extracted

    @staticmethod
    def _compare_string_lists(values_a: list[str], values_b: list[str]) -> dict[str, list[str]]:
        """比较两组字符串列表。"""

        set_a = set(values_a)
        set_b = set(values_b)
        return {
            "same_items": sorted(set_a & set_b),
            "only_a_items": sorted(set_a - set_b),
            "only_b_items": sorted(set_b - set_a),
        }

    def _assess_comparability(
        self,
        record_a: ArchivedRunRecord,
        record_b: ArchivedRunRecord,
        config_diff: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """给出两次运行的可比性判断。"""

        command_match = record_a.manifest.get("command_name") == record_b.manifest.get("command_name")
        end_date_match = record_a.manifest.get("end_date") == record_b.manifest.get("end_date")
        data_mode_match = record_a.manifest.get("data_mode") == record_b.manifest.get("data_mode")
        provider_match = record_a.manifest.get("provider_name") == record_b.manifest.get("provider_name")
        adj_match = record_a.manifest.get("adj_mode") == record_b.manifest.get("adj_mode")
        manual_risk_match = record_a.manifest.get("manual_risk_file") == record_b.manifest.get("manual_risk_file")

        major_changes = self._top_config_changes(config_diff)
        if not command_match:
            level = "low"
            reason = "两次运行的 command_name 不一致，不建议直接比较核心结果。"
        elif end_date_match and data_mode_match and provider_match and adj_match and manual_risk_match and not major_changes:
            level = "high"
            reason = "两次运行属于同类运行，关键输入基本一致，可直接比较 key summary。"
        else:
            level = "partial"
            reason = "两次运行同属可对比范围，但关键配置或输入存在变化，解释结果时需要谨慎。"
        return {
            "level": level,
            "reason": reason,
            "command_match": command_match,
            "end_date_match": end_date_match,
            "data_mode_match": data_mode_match,
            "provider_match": provider_match,
            "adj_mode_match": adj_match,
            "manual_risk_match": manual_risk_match,
        }

    def _top_config_changes(self, config_diff: dict[str, list[dict[str, Any]]], limit: int = 5) -> list[dict[str, Any]]:
        """提取最值得关注的配置差异。"""

        candidates = config_diff["changed_values"] + config_diff["added_keys"] + config_diff["removed_keys"]

        def score(item: dict[str, Any]) -> tuple[int, str]:
            path = item["path"]
            is_major = any(path.startswith(prefix) for prefix in self.MAJOR_CONFIG_PREFIXES)
            return (0 if is_major else 1, path)

        return sorted(candidates, key=score)[:limit]

    @staticmethod
    def _top_summary_changes(summary_diff_df: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
        """提取最值得关注的 summary 变化。"""

        if summary_diff_df.empty:
            return []
        working = summary_diff_df.loc[summary_diff_df["change_type"] != "same"].copy()
        if working.empty:
            return []
        numeric_mask = pd.to_numeric(working["absolute_change"], errors="coerce").notna()
        working["abs_score"] = pd.to_numeric(working["absolute_change"], errors="coerce").abs().fillna(-1.0)
        working.loc[~numeric_mask, "abs_score"] = -1.0
        working = working.sort_values(["abs_score", "key"], ascending=[False, True])
        return working.drop(columns=["abs_score"]).head(limit).to_dict(orient="records")

    def _build_attention_points(
        self,
        comparability: dict[str, Any],
        top_config_changes: list[dict[str, Any]],
        top_summary_changes: list[dict[str, Any]],
        artifact_diff: dict[str, list[dict[str, Any]]],
    ) -> list[str]:
        """生成最值得人工关注的差异点。"""

        points = [f"可比性判断: {comparability['level']}，原因：{comparability['reason']}"]
        if top_config_changes:
            points.append(f"最大配置差异: {top_config_changes[0]['path']}")
        if top_summary_changes:
            first = top_summary_changes[0]
            points.append(
                f"最大结果差异: {first['key']}，value_a={self._display_value(first['value_a'])}，value_b={self._display_value(first['value_b'])}"
            )
        path_only_changes = len(artifact_diff["changed_values"]) + len(artifact_diff["added_keys"]) + len(artifact_diff["removed_keys"])
        if path_only_changes:
            points.append("输出产物存在路径差异，请先区分路径变化与结果变化。")
        return points[:3]

    def _compare_status(self, record_a: ArchivedRunRecord, record_b: ArchivedRunRecord) -> str:
        """根据缺失文件情况判定 compare_status。"""

        missing_total = len(record_a.missing_files) + len(record_b.missing_files)
        critical_missing = sum(
            1
            for item in record_a.missing_files + record_b.missing_files
            if item.split(":")[0] in self.CRITICAL_FILES
        )
        if critical_missing >= 2:
            return "failed"
        if missing_total > 0:
            return "partial"
        return "success"

    @staticmethod
    def _has_changed_path(diff_payload: dict[str, list[dict[str, Any]]], prefix: str) -> bool:
        """判断某个路径前缀是否出现变化。"""

        for bucket in ["changed_values", "added_keys", "removed_keys"]:
            for item in diff_payload.get(bucket, []):
                if str(item.get("path", "")).startswith(prefix):
                    return True
        return False

    def _update_latest_compare_index(
        self,
        compare_id: str,
        compare_dir: Path,
        compare_manifest: dict[str, Any],
    ) -> None:
        """更新最近一次 compare 的索引。"""

        self.compare_root.mkdir(parents=True, exist_ok=True)
        latest_index_path = self.compare_root / "latest_compare_index.json"
        payload = {
            "compare_id": compare_id,
            "compare_dir": str(compare_dir),
            "compare_status": compare_manifest["compare_status"],
            "comparable_level": compare_manifest["comparable_level"],
            "compared_at": compare_manifest["compared_at"],
        }
        latest_index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _render_compare_report(
        self,
        record_a: ArchivedRunRecord,
        record_b: ArchivedRunRecord,
        compare_manifest: dict[str, Any],
        compare_summary: dict[str, Any],
        manifest_diff: dict[str, list[dict[str, Any]]],
        cli_diff: dict[str, list[dict[str, Any]]],
        config_diff: dict[str, list[dict[str, Any]]],
        artifact_diff: dict[str, list[dict[str, Any]]],
        notes_diff: dict[str, Any],
        summary_diff_df: pd.DataFrame,
        brief: bool,
    ) -> str:
        """渲染 Markdown 对比报告。"""

        lines = [
            "# 运行结果对比报告",
            "",
            "## 1. 比较目的说明",
            "- 本报告用于比较两次已归档运行的输入、配置、摘要结果与告警差异。",
            "- 当前系统仍定位为长期定投研究与人工确认辅助工具，本报告不等于自动决策建议。",
            "",
            "## 2. run_a / run_b 基本信息",
            f"- run_a: {record_a.run_dir}",
            f"- run_b: {record_b.run_dir}",
            f"- run_a command: {record_a.manifest.get('command_name', '')}",
            f"- run_b command: {record_b.manifest.get('command_name', '')}",
            f"- compare_status: {compare_manifest['compare_status']}",
            "",
            "## 3. 可比性判断",
            f"- comparable_level: {compare_manifest['comparable_level']}",
            f"- comparability_reason: {compare_summary['comparability_assessment']['reason']}",
        ]

        if not brief:
            lines.extend(
                [
                    "",
                    "## 4. CLI 参数差异",
                    self._render_diff_section(cli_diff),
                    "",
                    "## 5. 生效配置差异",
                    self._render_diff_section(config_diff, limit=20),
                    "",
                    "## 6. manual risk file / manual risk snapshot 差异",
                    f"- manual_risk_changed: {compare_summary['manual_risk_changed']}",
                    self._render_filtered_paths(config_diff, ["manual_risk_file_path", "manual_risk_flags_snapshot"]),
                ]
            )

        lines.extend(
            [
                "",
                "## 7. 关键 summary 指标差异",
                self._render_summary_diff(summary_diff_df),
                "",
                "## 8. 输出产物差异",
                self._render_diff_section(artifact_diff),
                "",
                "## 9. warnings / limitations 差异",
                self._render_notes_diff(notes_diff),
                "",
                "## 10. 最值得关注的差异摘要",
            ]
        )
        lines.extend([f"- {item}" for item in compare_summary["top_attention_points"]] or ["- 当前未发现高优先级差异。"])
        lines.extend(
            [
                "",
                "## 11. 结论与解释",
                f"- 最大配置差异: {compare_summary['top_config_changes'][0]['path'] if compare_summary['top_config_changes'] else '无'}",
                f"- 最大结果差异: {compare_summary['top_summary_changes'][0]['key'] if compare_summary['top_summary_changes'] else '无'}",
                f"- 纯路径差异不应直接解释为策略或回测结果差异，请结合 key_summary 与配置变更一起判断。",
                "",
                "## 12. 限制说明",
                "- 对比器第一版基于 JSON/CSV/Markdown 归档产物，不做复杂语义理解。",
                "- 若 run 目录缺失关键文件，对比结果会降级为 partial 或 failed，并在报告中列出缺失项。",
                "- 不同命令类型之间通常不建议直接比较收益或风险指标。",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_diff_section(diff_payload: dict[str, list[dict[str, Any]]], limit: int = 10) -> str:
        """渲染 added/removed/changed 结构化差异。"""

        lines: list[str] = []
        for bucket, label in [
            ("changed_values", "changed"),
            ("added_keys", "added"),
            ("removed_keys", "removed"),
        ]:
            items = diff_payload.get(bucket, [])[:limit]
            if not items:
                continue
            lines.append(f"- {label}:")
            for item in items:
                if bucket == "changed_values":
                    lines.append(f"  - {item['path']}: {item.get('value_a')} -> {item.get('value_b')}")
                elif bucket == "added_keys":
                    lines.append(f"  - {item['path']}: {item.get('value_b')}")
                else:
                    lines.append(f"  - {item['path']}: {item.get('value_a')}")
        return "\n".join(lines) if lines else "- 无结构化差异。"

    @staticmethod
    def _render_filtered_paths(diff_payload: dict[str, list[dict[str, Any]]], prefixes: list[str]) -> str:
        """只渲染命中特定前缀的差异。"""

        rows: list[str] = []
        for bucket in ["changed_values", "added_keys", "removed_keys"]:
            for item in diff_payload.get(bucket, []):
                if any(str(item.get("path", "")).startswith(prefix) for prefix in prefixes):
                    if bucket == "changed_values":
                        rows.append(f"- {item['path']}: {item.get('value_a')} -> {item.get('value_b')}")
                    elif bucket == "added_keys":
                        rows.append(f"- {item['path']}: {item.get('value_b')} (only run_b)")
                    else:
                        rows.append(f"- {item['path']}: {item.get('value_a')} (only run_a)")
        return "\n".join(rows) if rows else "- manual risk 相关配置无差异。"

    @staticmethod
    def _render_summary_diff(summary_diff_df: pd.DataFrame, limit: int = 15) -> str:
        """渲染关键 summary 差异。"""

        if summary_diff_df.empty:
            return "- 无 key summary。"
        working = summary_diff_df.loc[summary_diff_df["change_type"] != "same"].copy()
        if working.empty:
            return "- key summary 无差异。"
        lines = []
        for _, row in working.head(limit).iterrows():
            lines.append(
                f"- {row['key']}: value_a={RunCompareEngine._display_value(row['value_a'])}, "
                f"value_b={RunCompareEngine._display_value(row['value_b'])}, "
                f"direction={row['direction']}, "
                f"absolute_change={RunCompareEngine._display_value(row['absolute_change'])}, "
                f"relative_change={RunCompareEngine._display_value(row['relative_change'])}"
            )
        return "\n".join(lines)

    @staticmethod
    def _render_notes_diff(notes_diff: dict[str, Any]) -> str:
        """渲染 notes 差异。"""

        lines: list[str] = []
        for section_key, section_label in [
            ("warnings", "warnings"),
            ("limitations", "limitations"),
            ("extra_notes", "extra_notes"),
        ]:
            section = notes_diff.get(section_key, {})
            lines.append(f"- {section_label}:")
            lines.append(f"  - same_items: {section.get('same_items', [])}")
            lines.append(f"  - only_a_items: {section.get('only_a_items', [])}")
            lines.append(f"  - only_b_items: {section.get('only_b_items', [])}")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_for_json(data: Any) -> Any:
        """将 NaN 等非标准 JSON 值转为安全结构。"""

        if isinstance(data, dict):
            return {key: RunCompareEngine._sanitize_for_json(value) for key, value in data.items()}
        if isinstance(data, list):
            return [RunCompareEngine._sanitize_for_json(item) for item in data]
        if isinstance(data, float) and pd.isna(data):
            return None
        return data

    @staticmethod
    def _display_value(value: Any) -> Any:
        """渲染报告时优雅展示空值。"""

        if isinstance(value, float) and pd.isna(value):
            return ""
        return value
