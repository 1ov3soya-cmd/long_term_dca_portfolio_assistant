# Demo Asset Checklist

## Purpose

Use this checklist to prepare screenshots, terminal captures, and demo flow notes for:

- portfolio pages
- interviews
- walkthrough videos
- review meetings
- acceptance demos

The emphasis is clarity. Capture real archive-backed screens, not idealized mocks.

## Recommended Page Screenshots

### 1. Dashboard

Capture:

- latest run summary
- risk matrix
- latest compare summary
- latest research summary
- research / manual risk alignment summary

Why it matters:

- shows the project as a single research workstation
- demonstrates that archive-backed summaries are live

### 2. Run Compare

Capture:

- comparable level
- top config changes
- top summary changes
- summary diff table

Why it matters:

- shows traceability across runs
- shows how parameter and config changes are surfaced

### 3. Manual Risk

Capture:

- summary cards
- current manual risk table
- acceptance / validation source status

Why it matters:

- shows that manual governance is explicit
- demonstrates that the system does not rely only on price rules

### 4. Research

Capture:

- research list / table
- final research label
- confidence
- memo preview

Why it matters:

- shows the TradingAgents research enhancement as advisory output
- makes the PoC boundary visible

### 5. Research vs Manual Risk

Capture:

- matched / mismatched counts
- high-priority section
- one example row with mismatch details

Why it matters:

- shows the bridge between research suggestion and human risk governance
- highlights the read-only alignment workflow

## Recommended Terminal Screenshots

### Research generation

```bash
python -m src.main run-agent-research --symbol 600519 --end-date 2025-12-31
```

Capture:

- command
- success output
- generated archive path if shown

### Run comparison

```bash
python -m src.main compare-runs --run-a <run_id_or_path> --run-b <run_id_or_path>
```

Capture:

- command
- compare output path
- success status

### Frontend build

```bash
cd frontend
npm run build
```

Capture:

- successful build output
- final bundle summary

## Recommended Demo Order

1. Dashboard
   - explain that the UI is read-only
   - show latest archive summaries

2. Run Compare
   - explain run traceability
   - show config diff and summary diff

3. Manual Risk
   - explain pause / review / thesis broken states
   - show acceptance / validation sources

4. Research
   - explain TradingAgents PoC as research-only enhancement
   - show label, confidence, and memo

5. Research vs Manual Risk
   - show matched vs mismatched items
   - point out high-priority manual review objects

6. Documentation
   - briefly show README, acceptance notes, or final project summary

## Per-Page Talking Points

### Dashboard

- archive-backed summaries
- low-frequency workflow
- no auto-trading

### Run Compare

- comparable level
- structured diff rather than raw file diff

### Manual Risk

- human override layer
- no automatic sell execution

### Research

- advisory-only research output
- does not write back to live manual risk

### Research vs Manual Risk

- exposes gaps between suggestions and current risk state
- supports manual review prioritization

## Capture Quality Checklist

- [ ] browser language is set intentionally to `zh` or `en`
- [ ] screenshots use real archive-backed data
- [ ] no obviously stale timestamps are shown
- [ ] no placeholder mock text is visible
- [ ] no broken route or empty white screen is visible
- [ ] terminal screenshots show successful commands
- [ ] one screenshot includes Dashboard research summary card
- [ ] one screenshot includes alignment mismatch / high-priority state

## Optional Supporting Assets

- project directory tree screenshot
- `reports/project_status_summary.md`
- `reports/final_acceptance_report.md`
- `docs/portfolio_project_cn.md`
- `docs/portfolio_project_en.md`

Use these only as supporting material. The primary demo should still be the live pages and real archive outputs.
