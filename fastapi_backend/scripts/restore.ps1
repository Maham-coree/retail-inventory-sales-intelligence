param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z][A-Za-z0-9_]{0,62}$')]
    [string]$NewDatabaseName,
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$EnvironmentFile = (Join-Path $PSScriptRoot '..\.env')
)

$ErrorActionPreference = 'Stop'
$backup = (Resolve-Path -LiteralPath $BackupFile).Path
$envFile = (Resolve-Path -LiteralPath $EnvironmentFile).Path
$urlLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^\s*DATABASE_URL=' } | Select-Object -First 1
if (-not $urlLine) { throw 'DATABASE_URL was not found in the selected environment file.' }
$databaseUrl = $urlLine.Substring($urlLine.IndexOf('=') + 1).Trim().Trim('"').Trim("'")
$connectionUri = [Uri]$databaseUrl
$userInfo = $connectionUri.UserInfo.Split(':', 2)
if ($userInfo.Count -ne 2) { throw 'DATABASE_URL must include a username and password.' }

$root = 'C:\Program Files\PostgreSQL'
$bin = Get-ChildItem -LiteralPath $root -Directory -ErrorAction Stop |
    Sort-Object { [version]($_.Name + '.0') } -Descending |
    ForEach-Object { Join-Path $_.FullName 'bin' } |
    Where-Object {
        (Test-Path (Join-Path $_ 'pg_restore.exe')) -and
        (Test-Path (Join-Path $_ 'psql.exe'))
    } | Select-Object -First 1
if (-not $bin) { throw "Could not locate pg_restore.exe under $root." }

   Add-Type -AssemblyName System.Web
$query = [System.Web.HttpUtility]::ParseQueryString($connectionUri.Query)
$env:PGHOST = $connectionUri.Host
$env:PGPORT = if ($connectionUri.IsDefaultPort) { '5432' } else { [string]$connectionUri.Port }
$env:PGUSER = [Uri]::UnescapeDataString($userInfo[0])
$env:PGPASSWORD = [Uri]::UnescapeDataString($userInfo[1])
if ($query['sslmode']) { $env:PGSSLMODE = $query['sslmode'] }

try {
    & (Join-Path $bin 'psql.exe') --dbname=postgres --set=ON_ERROR_STOP=1 --command="CREATE DATABASE `"$NewDatabaseName`""
    if ($LASTEXITCODE -ne 0) { throw "Could not create the new database '$NewDatabaseName'; an existing database was not modified." }
    & (Join-Path $bin 'pg_restore.exe') --dbname=$NewDatabaseName --no-owner --exit-on-error $backup
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore failed. The live database was not targeted.' }
    Write-Output "Restore completed into new database: $NewDatabaseName"
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
