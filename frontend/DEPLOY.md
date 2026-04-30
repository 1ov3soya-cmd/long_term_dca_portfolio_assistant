# Frontend Static Deployment

The frontend supports two data modes:

- Local development mode: reads live local archives through `/archive-data/...` from the Vite middleware.
- Static snapshot mode: reads prebuilt JSON snapshots from `/data/*.json`, bundled into `frontend/dist`.

Static snapshot mode is a read-only research website. It does not auto-refresh data, place orders, sell positions, or modify `manual_risk_flags`.

## Deployment Model

1. Backend commands generate `reports/` archives.
2. `build-frontend-snapshot` converts the latest archives into `frontend/public/data/*.json`.
3. `npm run build` copies `public/data` into `dist/data`.
4. Deploy `frontend/dist` to a static hosting platform.
5. Visitors can open the website without Python or local archive access.

## Generate Data Snapshots

From the repository root:

```powershell
python -m src.main suggest --end-date 2025-12-31
python -m src.main backtest --end-date 2025-12-31
python -m src.main validate-manual-risk-flags
python -m src.main run-monthly-research --end-date 2025-12-31
python -m src.main build-frontend-snapshot --end-date 2025-12-31
```

The snapshot command writes:

```text
frontend/public/data/site_manifest.json
frontend/public/data/archive_compat_snapshot.json
frontend/public/data/dashboard_snapshot.json
frontend/public/data/monthly_research_snapshot.json
frontend/public/data/manual_risk_snapshot.json
frontend/public/data/research_vs_manual_risk_snapshot.json
frontend/public/data/run_compare_snapshot.json
frontend/public/data/research_snapshot.json
```

`site_manifest.json` enables static snapshot mode. If it is missing, the frontend falls back to `/archive-data/...` for local development.

## Build And Preview

```powershell
cd frontend
npm install
npm run build
npm run preview
```

Open:

```text
http://localhost:4173
```

In preview, confirm:

```text
http://localhost:4173/data/site_manifest.json
```

returns JSON.

## GitHub Pages

GitHub Pages often serves project sites under a repository subpath:

```text
https://<user>.github.io/<repo-name>/
```

For that case, build with a matching Vite base path:

```powershell
cd frontend
$env:VITE_BASE_PATH="/<repo-name>/"
npm run build
Remove-Item Env:\VITE_BASE_PATH
```

Or use the root helper script:

```powershell
.\scripts\build_static_site.ps1 -EndDate "2025-12-31" -BasePath "/<repo-name>/"
```

On macOS/Linux:

```bash
./scripts/build_static_site.sh 2025-12-31 /<repo-name>/
```

Deploy the generated `frontend/dist` directory to GitHub Pages.

If deploying to a custom domain or an organization/user root site, use:

```text
VITE_BASE_PATH=/
```

The frontend snapshot loader follows Vite `BASE_URL`, so `/data/*.json` becomes `/<repo-name>/data/*.json` for GitHub Pages subpath deployments.

## Vercel

Recommended project settings:

```text
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
Framework Preset: Vite
```

This repo includes:

```text
frontend/vercel.json
```

Before deploying, make sure `frontend/public/data/*.json` has been generated and committed or otherwise included in the deployment source.

For Vercel root deployments, the default base path `/` is correct. No API server is required.

## Netlify

Recommended project settings:

```text
Base directory: frontend
Build command: npm run build
Publish directory: frontend/dist
```

If Netlify's base directory is set to `frontend`, the publish directory can be:

```text
dist
```

This repo includes:

```text
frontend/netlify.toml
```

As with Vercel, generate `frontend/public/data/*.json` before the Netlify build.

## Static Data Update Flow

The deployed site is static. To update the displayed data:

```powershell
python -m src.main build-frontend-snapshot --end-date 2025-12-31
cd frontend
npm run build
```

Then redeploy:

```text
frontend/dist
```

Do not deploy the raw `reports/` directory. The website only needs `dist`, including `dist/data/*.json`.

## Optional Helper Scripts

Windows:

```powershell
.\scripts\build_static_site.ps1 -EndDate "2025-12-31" -BasePath "/"
```

macOS/Linux:

```bash
./scripts/build_static_site.sh 2025-12-31 /
```

For GitHub Pages project sites, pass `/<repo-name>/` as the base path.

## Pages Included

- Dashboard: archive summary, monthly suggestion details, monthly research summary, and alignment summary.
- Run Compare: latest compare archive, config diff, summary diff, and report preview.
- Manual Risk: acceptance, validation, and fallback manual risk data.
- Research: single-symbol TradingAgents PoC research output.
- Monthly Research: monthly debate batch output.
- Research vs Manual Risk: read-only comparison between research suggestions and current manual risk state.

## Boundary Notes

- No API server is required for the deployed site.
- The static site does not auto-refresh data.
- The static site does not execute trades.
- The static site does not auto-sell.
- The static site does not modify `manual_risk_flags`.
- TradingAgents and monthly research outputs remain advisory-only.

## Troubleshooting

- Empty page data: check `frontend/public/data/site_manifest.json` before build and `frontend/dist/data/site_manifest.json` after build.
- GitHub Pages missing assets: confirm `VITE_BASE_PATH` matches the repository subpath.
- Stale Dashboard data: rerun `build-frontend-snapshot`, rebuild, and redeploy.
- Unexpected `N/A`: confirm the corresponding source archive exists before generating snapshots.
