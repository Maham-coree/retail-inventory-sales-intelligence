param(
    [string]$EnvironmentFile = (Join-Path $PSScriptRoot '..\.env')
)

$ErrorActionPreference = 'Stop'
$envFile = (Resolve-Path -LiteralPath $EnvironmentFile).Path
$urlLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^\s*DATABASE_URL=' } | Select-Object -First 1
if (-not $urlLine) { throw 'DATABASE_URL was not found in the selected environment file.' }
$databaseUrl = $urlLine.Substring($urlLine.IndexOf('=') + 1).Trim().Trim('"').Trim("'")
$connectionUri = [Uri]$databaseUrl
$userInfo = $connectionUri.UserInfo.Split(':', 2)
if ($userInfo.Count -ne 2) { throw 'DATABASE_URL must include a username and password.' }

$root = 'C:\Program Files\PostgreSQL'
$bin = Get-ChildItem -LiteralPath $root -Directory -ErrorAction Stop |
    Sort-Object { [version]$_.Name } -Descending |
    ForEach-Object { Join-Path $_.FullName 'bin' } |
    Where-Object { (Test-Path (Join-Path $_ 'pg_dump.exe')) -and (Test-Path (Join-Path $_ 'psql.exe')) } |
    Select-Object -First 1
if (-not $bin) { throw "Could not locate pg_dump.exe under $root." }

$query = [System.Web.HttpUtility]::ParseQueryString($connectionUri.Query)
$env:PGHOST = $connectionUri.Host
$env:PGPORT = if ($connectionUri.IsDefaultPort) { '5432' } else { [string]$connectionUri.Port }
$env:PGUSER = [Uri]::UnescapeDataString($userInfo[0])
$env:PGPASSWORD = [Uri]::UnescapeDataString($userInfo[1])
$env:PGDATABASE = [Uri]::UnescapeDataString($connectionUri.AbsolutePath.TrimStart('/'))
if ($query['sslmode']) { $env:PGSSLMODE = $query['sslmode'] }

$backupDir = Join-Path $PSScriptRoot '..\backups'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$customFile = Join-Path $backupDir "retail-$stamp.dump"
$plainFile = Join-Path $backupDir "retail-$stamp.sql"
try {
    & (Join-Path $bin 'pg_dump.exe') --format=custom --file=$customFile
    if ($LASTEXITCODE -ne 0) { throw 'Custom-format pg_dump failed.' }
    & (Join-Path $bin 'pg_dump.exe') --format=plain --file=$plainFile
    if ($LASTEXITCODE -ne 0) { throw 'Plain SQL pg_dump failed.' }
    Write-Output "Backup completed: $customFile and $plainFile"
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:PGDATABASE -ErrorAction SilentlyContinue
}
