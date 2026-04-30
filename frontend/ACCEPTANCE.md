# Frontend Acceptance

## Basic Startup

```bash
cd frontend
npm run dev
```

Open these routes:

- `#/`
- `#/compare`
- `#/manual-risk`
- `#/research`
- `#/research-manual-risk`

Expected:

- each page is reachable
- the top navigation works
- the active page has a visible active state
- `zh / en` switching updates the UI immediately

## Dashboard

Expected:

- reads real archive summaries when archive files are available
- `Latest Research Summary` card shows research data when available
- `Research / Manual Risk Alignment` card shows matched / mismatched / high-priority summary when available
- both cards degrade gracefully when source files are missing

## Run Compare

Expected:

- reads latest compare archive data
- still renders partial data when `compare_summary.json`, `summary_diff.csv`, or `compare_report.md` is missing
- does not white-screen on partial archive input

## Manual Risk

Expected:

- reads acceptance / validation / fallback data
- shows pause buy / force review / thesis broken / effective_from / note
- does not white-screen when one source is missing

## Research

Expected:

- reads `research_index.json`
- shows research table and memo preview
- research body text remains readable and is not incorrectly translated

## Research vs Manual Risk

Expected:

- builds matched / mismatched / high-priority results
- marks high priority when `suggestThesisBroken=true` and `manualThesisBroken=false`
- still renders partial data when only one side is available

## Language Switching

Check both `zh` and `en` for:

- page titles
- card titles
- table headers
- loading / empty / partial / error text
- navigation labels

## Build

```bash
cd frontend
npm run build
```

Expected:

- build succeeds
- no new compile errors

## Known Limits

- the frontend depends on archive files existing on disk
- it reads JSON / Markdown / CSV only
- it is still read-only and does not execute trading actions
