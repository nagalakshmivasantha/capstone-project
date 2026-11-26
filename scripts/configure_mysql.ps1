$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$password = Read-Host "Enter the existing MySQL root password" -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new("", $password).Password

$content = @"
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=capstone
MYSQL_USER=root
MYSQL_PASSWORD=$plainPassword
MYSQL_CONNECTION_TIMEOUT=3

QUALITY_DB_PATH=app/artifacts/platform.db
QUALITY_JOB_WORKERS=2
QUALITY_JOB_MAX_ATTEMPTS=3
"@

Set-Content -Path $envPath -Value $content -Encoding utf8
Remove-Variable plainPassword, password
Write-Host "Saved MySQL configuration to the local ignored .env file."
Write-Host "The password was not printed."
