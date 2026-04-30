# Archive Freshness Checklist

## Purpose

Use this checklist before a demo, review, interview walkthrough, or release snapshot.

The goal is simple:

- confirm that the archive files still exist
- confirm that the latest pointers are current
- confirm that the frontend is reading recent outputs rather than stale data

This is not a deep validation procedure. It is a lightweight freshness pass.

## Key Files To Check

### Run archive

- `reports/runs/latest_index.json`
- latest `suggest` run directory
- latest `backtest` run directory
- latest `validate-data` run directory
- latest `validate-backtest` run directory
- latest `sensitivity-test` run directory
- latest `summarize-robustness` run directory
- latest `validate-manual-risk-flags` run directory
- latest `run-agent-research` run directory

### Compare archive

- `reports/run_compare/latest_compare_index.json`
- latest compare directory under `reports/run_compare/`

### Manual risk files

- `reports/manual/manual_logic_risk_acceptance_report.json`
- `reports/manual/manual_logic_risk_acceptance_preview.csv`
- `reports/manual/manual_risk_flags_validation.json`
- `reports/manual/manual_risk_flags_validation.md`
- `reports/manual_logic_risk_acceptance_checklist.md`

### Research files

- `reports/agent_research/research_index.json`
- referenced research JSON files
- referenced research Markdown memo files

## What To Check

For each key archive or pointer file, confirm:

- the file path exists
- the timestamp is recent enough for the current demo or review
- the JSON can be opened
- the referenced output path exists
- `key_summary.json` exists when a run summary is expected
- `output_artifacts.json` exists when a run report is expected
- the frontend page that depends on the file still renders a visible summary

## Suggested Release-Prep Order

1. Check backend pointers first
   - open `reports/runs/latest_index.json`
   - open `reports/run_compare/latest_compare_index.json`
   - open `reports/agent_research/research_index.json`

2. Check recent run directories
   - latest `suggest`
   - latest `backtest`
   - latest `compare-runs`
   - latest `run-agent-research`
   - latest `validate-manual-risk-flags`

3. Check manual risk artifacts
   - acceptance report
   - preview CSV
   - validation JSON / Markdown

4. Start the frontend and verify the pages
   - Dashboard
   - Run Compare
   - Manual Risk
   - Research
   - Research vs Manual Risk

## Quick Checklist

### Backend pointers

- [ ] `reports/runs/latest_index.json` exists
- [ ] `reports/run_compare/latest_compare_index.json` exists
- [ ] `reports/agent_research/research_index.json` exists

### Latest run directories

- [ ] latest `suggest` run directory exists
- [ ] latest `backtest` run directory exists
- [ ] latest `compare-runs` run directory exists
- [ ] latest `run-agent-research` run directory exists
- [ ] latest `validate-manual-risk-flags` run directory exists

### Run contents

- [ ] latest `suggest` run has `run_manifest.json`
- [ ] latest `backtest` run has `key_summary.json`
- [ ] latest `compare-runs` run has `output_artifacts.json`
- [ ] latest `run-agent-research` run has `output_artifacts.json`
- [ ] latest `validate-manual-risk-flags` run has `output_artifacts.json`

### Manual risk artifacts

- [ ] acceptance report exists
- [ ] acceptance preview CSV exists
- [ ] validation JSON exists
- [ ] validation Markdown exists

### Research artifacts

- [ ] `research_index.json` contains at least one item
- [ ] referenced research JSON file exists
- [ ] referenced research Markdown file exists

### Frontend display

- [ ] Dashboard shows real archive summaries
- [ ] Dashboard shows research summary card or a graceful empty state
- [ ] Dashboard shows alignment summary card or a graceful empty state
- [ ] Run Compare page loads latest compare data or a graceful partial state
- [ ] Manual Risk page loads acceptance / validation data or a graceful fallback
- [ ] Research page loads `research_index.json` or a graceful empty state
- [ ] Research vs Manual Risk page shows matched / mismatched summary or a graceful partial state

## If Something Is Stale

Use the smallest command that refreshes the missing area:

### Refresh compare data

```bash
python -m src.main compare-runs --run-a <run_id_or_path> --run-b <run_id_or_path>
```

### Refresh manual risk validation

```bash
python -m src.main validate-manual-risk-flags
```

### Refresh research data

```bash
python -m src.main run-agent-research --symbol 600519 --end-date 2025-12-31
```

### Refresh dashboard-facing run outputs

```bash
python -m src.main suggest --end-date 2025-12-31
python -m src.main backtest --end-date 2025-12-31
```
