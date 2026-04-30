import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.main as main_module


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cli_command_registry_smoke_fixed() -> None:
    """Critical CLI entry points remain registered on the parser."""
    parser = main_module.build_parser()
    command_action = next(action for action in parser._actions if getattr(action, "dest", "") == "command")
    commands = set(command_action.choices)

    expected = {
        "suggest",
        "backtest",
        "validate-data",
        "validate-backtest",
        "sensitivity-test",
        "summarize-robustness",
        "validate-manual-risk-flags",
        "compare-runs",
        "run-agent-research",
    }
    assert expected.issubset(commands)


def test_archive_roots_exist_smoke_fixed() -> None:
    """Critical archive directories and index files exist."""
    required_paths = [
        PROJECT_ROOT / "reports" / "runs",
        PROJECT_ROOT / "reports" / "run_compare",
        PROJECT_ROOT / "reports" / "manual",
        PROJECT_ROOT / "reports" / "agent_research",
        PROJECT_ROOT / "reports" / "runs" / "latest_index.json",
        PROJECT_ROOT / "reports" / "run_compare" / "latest_compare_index.json",
        PROJECT_ROOT / "reports" / "agent_research" / "research_index.json",
        PROJECT_ROOT / "reports" / "manual" / "manual_logic_risk_acceptance_report.json",
        PROJECT_ROOT / "reports" / "manual" / "manual_risk_flags_validation.json",
    ]

    missing = [str(path) for path in required_paths if not path.exists()]
    assert not missing, f"Missing required archive paths: {missing}"


def test_latest_index_entries_parse_smoke_fixed() -> None:
    """latest_index.json parses and points to key run directories."""
    latest_index_path = PROJECT_ROOT / "reports" / "runs" / "latest_index.json"
    latest_index = _load_json(latest_index_path)

    for command_name in ["suggest", "backtest", "compare-runs", "run-agent-research"]:
        if command_name not in latest_index:
            continue
        entry = latest_index[command_name]
        assert isinstance(entry, dict)
        assert entry.get("run_id")
        run_dir = PROJECT_ROOT / "reports" / "runs" / entry["run_id"]
        assert run_dir.exists(), f"Run directory not found for {command_name}: {run_dir}"
        assert (run_dir / "run_manifest.json").exists()


def test_compare_archive_index_parse_smoke_fixed() -> None:
    """Compare archive index parses and resolves compare_manifest."""
    compare_index_path = PROJECT_ROOT / "reports" / "run_compare" / "latest_compare_index.json"
    compare_index = _load_json(compare_index_path)

    assert isinstance(compare_index, dict)
    compare_id = compare_index.get("compare_id")
    compare_path = compare_index.get("compare_path")
    assert compare_id or compare_path

    if compare_path:
        compare_dir = PROJECT_ROOT / compare_path
    else:
        compare_dir = PROJECT_ROOT / "reports" / "run_compare" / compare_id

    assert compare_dir.exists()
    assert (compare_dir / "compare_manifest.json").exists()


def test_research_index_parse_smoke_fixed() -> None:
    """research_index.json parses and resolves at least one research artifact."""
    research_index_path = PROJECT_ROOT / "reports" / "agent_research" / "research_index.json"
    research_index = _load_json(research_index_path)

    assert isinstance(research_index, dict)
    items = research_index.get("items", [])
    assert isinstance(items, list)
    assert items, "research_index.json has no items"

    first_item = items[0]
    assert first_item.get("symbol")
    assert first_item.get("analysis_date")

    json_relative_path = first_item.get("json_relative_path")
    markdown_relative_path = first_item.get("markdown_relative_path")

    if json_relative_path:
        assert (PROJECT_ROOT / json_relative_path).exists()
    if markdown_relative_path:
        assert (PROJECT_ROOT / markdown_relative_path).exists()
