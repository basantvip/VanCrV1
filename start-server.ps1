# Start VanCr Backend Server
# Uses Azure Key Vault for secrets - requires Azure CLI login
Set-Location C:\Users\bagrawal\OneDrive\VanCrV1

# Set Key Vault name (secrets are retrieved from Key Vault by the app)
$env:KEY_VAULT_NAME='kv-vancr-prod'

Write-Host "Starting VanCr Backend Server on http://localhost:8000" -ForegroundColor Green
Write-Host "Using Azure Key Vault: kv-vancr-prod" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

& "C:\Users\bagrawal\OneDrive\VanCrV1\.venv\Scripts\python.exe" backend\app.py
