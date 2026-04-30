# Frontend Usage

## Scope

The `frontend` subproject is a read-only research dashboard. It reads archived JSON / Markdown / CSV outputs from the project root and renders them in the browser.

It does not:

- place orders
- auto-write back to `manual_risk_flags`
- run strategy calculations
- execute trades

## Start

```bash
cd frontend
npm install
npm run dev
```

Production build:

```bash
cd frontend
npm run build
```

## Archive Data

The frontend reads live archive files through the Vite middleware path:

- `/archive-data/reports/runs/...`
- `/archive-data/reports/run_compare/...`
- `/archive-data/reports/manual/...`
- `/archive-data/reports/agent_research/...`
- `/archive-data/config/...`

The UI does not call a Python API. It reads archive files directly.

## Pages

### `#/`
Dashboard overview for:

- latest run snapshots
- config summary
- risk matrix
- monthly suggestion summary
- latest backtest summary
- manual risk summary
- robustness summary
- latest compare summary
- latest research summary
- research / manual risk alignment summary

### `#/compare`
Archived run comparison view.

### `#/manual-risk`
Current manual logic risk view.

### `#/research`
TradingAgents research output view.

### `#/research-manual-risk`
Read-only comparison between research suggestions and current manual risk state.

## Required Files

### Dashboard

- `reports/runs/latest_index.json`
- latest run directory files such as `run_manifest.json`, `key_summary.json`, `effective_config_snapshot.json`, `output_artifacts.json`

### Run Compare

- `reports/run_compare/latest_compare_index.json`
- `reports/run_compare/<compare_id>/compare_manifest.json`
- `reports/run_compare/<compare_id>/compare_summary.json`

Optional but used when present:

- `compare_report.md`
- `config_diff.json`
- `summary_diff.csv`

### Manual Risk

Preferred sources:

- `reports/manual/manual_logic_risk_acceptance_report.json`
- `reports/manual/manual_logic_risk_acceptance_preview.csv`
- `reports/manual/manual_risk_flags_validation.json`
- `reports/manual_logic_risk_acceptance_checklist.md`
- `reports/manual/manual_risk_flags_validation.md`

Fallback sources:

- latest `validate-manual-risk-flags` run
- `config/manual_risk_flags.json`
- `config/manual_risk_flags_acceptance_sample.json`

### Research

Preferred sources:

- `reports/agent_research/research_index.json`
- referenced research JSON / Markdown files

Fallback source:

- latest `run-agent-research` run

### Research vs Manual Risk

This page reuses Research data and Manual Risk data, then builds a read-only alignment snapshot in the frontend adapter layer.

## Empty States

If a page shows empty data, run the corresponding command first.

### Compare

```bash
python -m src.main compare-runs --run-a <run_id_or_path> --run-b <run_id_or_path>
```

### Manual Risk

```bash
python -m src.main validate-manual-risk-flags
```

### Research

```bash
python -m src.main run-agent-research --symbol 600519 --end-date 2025-12-31
```

### Research vs Manual Risk

```bash
python -m src.main run-agent-research --symbol 600519 --end-date 2025-12-31
python -m src.main validate-manual-risk-flags
```

## Routes

- `#/`
- `#/compare`
- `#/manual-risk`
- `#/research`
- `#/research-manual-risk`

## Read-only Notice

The frontend is a read-only presentation layer. Research, Manual Risk, Compare, and Dashboard outputs are for human review only.
