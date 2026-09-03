$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $root ".env"

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host " VNSTOCK SPONSOR BRONZE - LOCAL CREDENTIAL SETUP" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "The API key is stored only in .env on this PC." -ForegroundColor Yellow
Write-Host ".env is excluded by .gitignore and must NOT be committed." -ForegroundColor Yellow
Write-Host ""

$secure = Read-Host "Paste VNSTOCK Sponsor API Key" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
if ([string]::IsNullOrWhiteSpace($apiKey)) { throw "API key cannot be empty." }

$defaultVenv = ""
$localVenv = Join-Path $root ".venv"
if (Test-Path (Join-Path $localVenv "Scripts\python.exe")) { $defaultVenv = $localVenv }
$venv = Read-Host "Sponsor venv path (Enter to use '$defaultVenv' or system Python)"
if ([string]::IsNullOrWhiteSpace($venv)) { $venv = $defaultVenv }

$content = @(
    "# LOCAL ONLY - DO NOT COMMIT",
    "VNSTOCK_API_KEY=$apiKey",
    "VNSTOCK_INTERACTIVE=0",
    "VNSTOCK_LANGUAGE=2"
)
if (-not [string]::IsNullOrWhiteSpace($venv)) { $content += "VNSTOCK_VENV_PATH=$venv" }
Set-Content -Path $envFile -Value $content -Encoding UTF8

# Also set it for the current user so vnstock-installer and Sponsor libraries
# can detect the key outside this project if needed.
[Environment]::SetEnvironmentVariable("VNSTOCK_API_KEY", $apiKey, "User")
if (-not [string]::IsNullOrWhiteSpace($venv)) {
    [Environment]::SetEnvironmentVariable("VNSTOCK_VENV_PATH", $venv, "User")
}

Write-Host ""
Write-Host "OK - local .env created: $envFile" -ForegroundColor Green
Write-Host "OK - VNSTOCK_API_KEY also saved as a Windows User environment variable." -ForegroundColor Green
Write-Host "Next: run RUN_DIAGNOSE_VNSTOCK.bat, then RUN_FULL_REFRESH.bat" -ForegroundColor Cyan
