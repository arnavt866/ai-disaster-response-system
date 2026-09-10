# Post-start smoke test for docker compose stack.
$ErrorActionPreference = "Stop"

$Api = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8000" }
$Ui = if ($env:UI_URL) { $env:UI_URL } else { "http://localhost:3000" }

Write-Host "==> Health: GET $Api/"
(Invoke-RestMethod -Uri "$Api/") | ConvertTo-Json -Compress

Write-Host "==> Dashboard: GET $Api/analytics/dashboard"
(Invoke-RestMethod -Uri "$Api/analytics/dashboard") | ConvertTo-Json -Compress | ForEach-Object { $_.Substring(0, [Math]::Min(400, $_.Length)) }

Write-Host "==> Frontend: GET $Ui/"
$response = Invoke-WebRequest -Uri "$Ui/" -UseBasicParsing
Write-Host "HTTP $($response.StatusCode)"
if ($response.StatusCode -ne 200) { exit 1 }

Write-Host "Smoke test passed."
