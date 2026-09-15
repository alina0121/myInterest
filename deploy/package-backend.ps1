# =============================================================
# Backend one-click packaging script (v0.3)
# Usage:  powershell -ExecutionPolicy Bypass -File deploy\package-backend.ps1
# Output: deploy/backend_dist.tar.gz
# =============================================================

$ErrorActionPreference = "Stop"

# ---------------- CONFIG ----------------
# Project root (edit if you move the project)
$ROOT    = "D:\myProject\myInvestTools"
# Server domain (host for scp/ssh)
$SERVER  = "api.icefun.cn"
# Remote project root on server
$REMOTE_ROOT = "/opt/myinvesttools"
# Pack local SQLite db and overwrite server one (true=overwrite, false=keep server data)
$INCLUDE_DB  = $true
# Pack local .env (set false to keep server .env e.g. prod secret keys)
$INCLUDE_ENV = $true
# --------------------------------------

$BACKEND   = Join-Path $ROOT "backend"
$OUT_DIR   = Join-Path $ROOT "deploy"
$TAR       = "backend_dist.tar.gz"
$OUT_PATH  = Join-Path $OUT_DIR $TAR

# [1/4] merge SQLite WAL into main db => clean .db for upload
Write-Host ("[1/4] Merging SQLite WAL..." -f 1) -ForegroundColor Cyan
$py = if (Test-Path (Join-Path $BACKEND ".venv\Scripts\python.exe")) { Join-Path $BACKEND ".venv\Scripts\python.exe" } else { "python" }
& $py -c "import sqlite3; c=sqlite3.connect(r'$BACKEND\data\xi.db', isolation_level=None); c.execute('PRAGMA wal_checkpoint(TRUNCATE)'); c.close(); print('  WAL merged OK')" 2>&1 | ForEach-Object { Write-Host ("  $_") -ForegroundColor Gray }

# [2/4] tar package (via Python tarfile, more reliable than system tar on Windows)
Write-Host "[2/4] Packaging..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $OUT_DIR | Out-Null

Push-Location $BACKEND
try {
    $paths = "app scripts data requirements.txt main.py"
    if ($INCLUDE_ENV -and (Test-Path ".env")) { $paths += " .env" }

    # heredoc-ish: inline python using environment to pass args
    $env:PW_BACKEND = $BACKEND
    $env:PW_OUT     = $OUT_PATH
    $env:PW_PATHS   = $paths -replace ' ', ';'   # split on ; in python
    $env:PW_INCLUDE_DB  = [string]$INCLUDE_DB
    $env:PW_INCLUDE_ENV = [string]$INCLUDE_ENV

    $pyCode = @'
import os, tarfile, sys, re
backend = os.environ["PW_BACKEND"]
out     = os.environ["PW_OUT"]
paths   = [p for p in os.environ["PW_PATHS"].split(";") if p]
incl_db = os.environ["PW_INCLUDE_DB"] == "True"
incl_env= os.environ["PW_INCLUDE_ENV"] == "True"

exc = ["__pycache__", ".venv", ".pytest_cache", ".git",
       lambda p: p.endswith(".db-shm") or p.endswith(".db-wal"),
       lambda p: p.startswith(os.path.join("data","backups"))]
def skip(p, arc):
    b = os.path.basename(arc)
    if "__pycache__" in arc or b in (".venv",".pytest_cache",".git"): return True
    if arc.endswith(".db-shm") or arc.endswith(".db-wal"): return True
    if arc.startswith(os.path.join("data","backups")): return True
    if not incl_db and arc.startswith("data"): return True
    if not incl_env and arc == ".env": return True
    return False
with tarfile.open(out, "w:gz") as tf:
    for p in paths:
        if not os.path.exists(p): continue
        tf.add(p, arcname=p, filter=lambda ti: (None if skip(ti.name, ti.name) else ti))
print("  packaged:", ", ".join(paths))
sys.exit(0)
'@
    $py | Out-Null
    $env:PW_CODE = $pyCode
    & $py -c "import os;exec(os.environ['PW_CODE'])" 
    if ($LASTEXITCODE -ne 0) { throw "python tar exit code $LASTEXITCODE" }
    Remove-Item Env:PW_BACKEND,Env:PW_OUT,Env:PW_PATHS,Env:PW_INCLUDE_DB,Env:PW_INCLUDE_ENV,Env:PW_CODE -ErrorAction SilentlyContinue
}
finally { Pop-Location }

# [3/4] verify
Write-Host "[3/4] Verifying..." -ForegroundColor Cyan
if (-not (Test-Path $OUT_PATH)) { throw "packaging failed: $OUT_PATH not generated" }
$size = (Get-Item $OUT_PATH).Length
Write-Host ("  output: {0}  ({1} MB)" -f $OUT_PATH, [math]::Round($size/1MB,2)) -ForegroundColor Green

# [4/4] print next steps for server deploy
Write-Host "[4/4] Done! Next server steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host ("  scp {0} {1}:{2}/" -f $OUT_PATH, $SERVER, $REMOTE_ROOT) -ForegroundColor Yellow
Write-Host ("  ssh {0} 'cd {1} && tar -xzf backend_dist.tar.gz -C backend --strip-components=1 && cd backend && .venv/bin/pip install -r requirements.txt -q && systemctl restart myinvesttools'" -f $SERVER, $REMOTE_ROOT) -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: stop the service first if the archive contains data/ (avoid SQLite lock)." -ForegroundColor Gray