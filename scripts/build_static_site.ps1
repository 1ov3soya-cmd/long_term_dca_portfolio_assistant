param(
  [string]$EndDate = "2025-12-31",
  [string]$BasePath = "/"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $RepoRoot "frontend"

Push-Location $RepoRoot
try {
  python -m src.main build-frontend-snapshot --end-date $EndDate
}
finally {
  Pop-Location
}

Push-Location $FrontendDir
try {
  npm install
  $env:VITE_BASE_PATH = $BasePath
  npm run build
}
finally {
  Remove-Item Env:\VITE_BASE_PATH -ErrorAction SilentlyContinue
  Pop-Location
}
