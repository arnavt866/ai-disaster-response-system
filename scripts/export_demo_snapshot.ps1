# Export a PostgreSQL data-only snapshot from the live dev database.
#
# Output: backend/snapshots/demo_snapshot.sql.gz (gzipped plain SQL).
#
# Plain SQL is used rather than pg_dump's custom format on purpose: pg_dump
# always writes the newest custom-format header version and has no flag to
# target an older one, so a dump taken with pg_dump 17/18 cannot be read by the
# older pg_restore shipped in the backend image. Plain SQL is portable text that
# any psql version can replay.
#
# Data only: the Docker entrypoint runs `alembic upgrade head` first, so the
# schema already exists. alembic_version and spatial_ref_sys are excluded --
# migrations stamp the former and the PostGIS extension populates the latter.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = if ($env:ENV_FILE) { $env:ENV_FILE } else { Join-Path $Root "backend\.env" }
$Output = if ($env:OUTPUT) { $env:OUTPUT } else { Join-Path $Root "backend\snapshots\demo_snapshot.sql.gz" }
$OutputDir = Split-Path -Parent $Output

if (-not (Test-Path $EnvFile)) {
    Write-Error "Missing env file: $EnvFile"
}

$databaseUrl = $null
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*DATABASE_URL\s*=\s*(.+)\s*$') {
        $databaseUrl = $matches[1].Trim()
    }
}
if (-not $databaseUrl) {
    Write-Error "DATABASE_URL not found in $EnvFile"
}

$pgDump = if ($env:PG_DUMP) { $env:PG_DUMP } else { "pg_dump" }
if (-not (Get-Command $pgDump -ErrorAction SilentlyContinue)) {
    Write-Error "pg_dump not found on PATH. Install PostgreSQL client tools or set PG_DUMP."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$parsed = python -c @"
from urllib.parse import unquote, urlparse

url = '''$databaseUrl'''.replace('postgresql+psycopg2://', 'postgresql://')
parsed = urlparse(url)
print(parsed.hostname or 'localhost')
print(parsed.port or 5432)
print(unquote(parsed.username or 'postgres'))
print(unquote(parsed.password or ''))
print((parsed.path or '/disaster_db').lstrip('/'))
"@

$lines = $parsed -split "`n"
$DbHost = $lines[0].Trim()
$DbPort = $lines[1].Trim()
$DbUser = $lines[2].Trim()
$DbPassword = $lines[3].Trim()
$DbName = $lines[4].Trim()

Write-Host "Exporting data-only snapshot from ${DbUser}@${DbHost}:${DbPort}/${DbName}"
Write-Host "Output: $Output"

$PlainSql = Join-Path $OutputDir "demo_snapshot.sql"

$env:PGPASSWORD = $DbPassword
& $pgDump -h $DbHost -p $DbPort -U $DbUser -d $DbName --data-only --format=plain --no-owner --no-acl --disable-triggers --exclude-table=alembic_version --exclude-table=spatial_ref_sys -f $PlainSql

if ($LASTEXITCODE -ne 0) {
    Write-Error "pg_dump failed with exit code $LASTEXITCODE"
}

Write-Host "Compressing to $Output ..."
if (Test-Path $Output) {
    Remove-Item $Output -Force
}
$inStream = [System.IO.File]::OpenRead($PlainSql)
$outStream = [System.IO.File]::Create($Output)
$gzipStream = New-Object System.IO.Compression.GzipStream($outStream, [System.IO.Compression.CompressionMode]::Compress)
try {
    $inStream.CopyTo($gzipStream)
} finally {
    $gzipStream.Dispose()
    $outStream.Dispose()
    $inStream.Dispose()
}
Remove-Item $PlainSql -Force

$sizeBytes = (Get-Item $Output).Length
$sizeMb = [math]::Round($sizeBytes / 1MB, 2)
Write-Host "Snapshot complete: $sizeMb MB ($sizeBytes bytes)"

Write-Host "Row-count spot check (live source DB):"
$spotCheck = @"
SELECT 'disaster_zones' AS table_name, COUNT(*)::bigint AS row_count FROM disaster_zones
UNION ALL SELECT 'buildings', COUNT(*)::bigint FROM buildings
UNION ALL SELECT 'relief_centers', COUNT(*)::bigint FROM relief_centers
UNION ALL SELECT 'disaster_events', COUNT(*)::bigint FROM disaster_events
UNION ALL SELECT 'ndma_alerts', COUNT(*)::bigint FROM ndma_alerts
UNION ALL SELECT 'satellite_assessments', COUNT(*)::bigint FROM satellite_assessments
UNION ALL SELECT 'allocation_records', COUNT(*)::bigint FROM allocation_records
ORDER BY table_name;
"@
& psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -At -F '|' -c $spotCheck

Write-Host "Restore path for Docker: mount $Output at /app/snapshots/demo_snapshot.sql.gz"
