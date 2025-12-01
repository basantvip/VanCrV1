# Azure Functions for VanCr Contact Form

## SaveContact Function
Appends a new submission to an Excel workbook stored as a blob in your Azure Storage Account.

### App Settings Required
- Option A (connection string mode):
  - `AZURE_STORAGE_CONNECTION_STRING`: Full connection string for the storage account.
  - `EXCEL_CONTAINER`: Container name (e.g. `forms`).
  - `EXCEL_BLOB_NAME`: Excel file name (e.g. `contact.xlsx`).
- Option B (direct SAS mode):
  - `EXCEL_SAS_URL`: Full SAS URL pointing directly to the blob (includes `?sv=...&se=...&sp=...`).
  - (Container & file name are ignored for SAS mode, but defaults remain for response metadata.)

### How It Works
1. HTTP POST to `/api/save-contact` with JSON body: `{ "phone": "...", "email": "...", "message": "..." }`.
2. If using connection string, ensures container exists; if SAS URL given, targets that blob directly.
3. Attempts a short lease (ignored if not permitted by SAS) to reduce collision risk.
4. Downloads existing Excel (or initializes headers) then appends a row.
5. Uploads modified workbook; releases lease if held.

### Deployment Outline
```bash
# In Cloud Shell or local with Azure CLI
az functionapp create -n vancr-func -g rg-vancr-prod -s stvancrprod -c centralindia --consumption-plan-location centralindia --runtime node --functions-version 4

# App settings
az functionapp config appsettings set -n vancr-func -g rg-vancr-prod --settings \
  AZURE_STORAGE_CONNECTION_STRING="<connection-string>" \
  EXCEL_CONTAINER="forms" \
  EXCEL_BLOB_NAME="contact.xlsx"

# OR (SAS mode)
az functionapp config appsettings set -n vancr-func -g rg-vancr-prod --settings \
  EXCEL_SAS_URL="https://account.blob.core.windows.net/forms/contact.xlsx?<sas-token>"
```

### GitHub Actions Deployment
Workflow added at `.github/workflows/deploy-function.yml` expects two repository secrets:
- `FUNCTIONAPP_PUBLISH_PROFILE`: Paste the XML publish profile content from Portal > Function App > Deployment Center > Get publish profile.
- `EXCEL_SAS_URL`: Your blob SAS URL.

On push to `main` affecting `azure-functions/**` it will:
1. Install dependencies.
2. Deploy the Functions package.
3. Set `EXCEL_SAS_URL` app setting.

### Generating SAS URL
Portal > Storage Account > Containers > forms > contact.xlsx > Generate SAS.
Include permissions: Read, Write, Create. Set expiry far enough in future. Regenerate before expiry and update secret & app setting.

### Local Run
```bash
npm install @azure/storage-blob exceljs uuid
func start
curl -X POST http://localhost:7071/api/save-contact -H "Content-Type: application/json" -d '{"phone":"123","email":"a@b.com","message":"Hello"}'
```

### Frontend Integration
Add endpoint override in `contact.html`:
```html
<script>
window.EMAIL_ENDPOINT = "https://vancr-func.azurewebsites.net/api/save-contact";
</script>
```

### Concurrency Notes
- Blob lease (60s) is attempted. If SAS token lacks lease permission, function continues without it.
- Low traffic sites are fine; for higher volume (> few writes/sec) prefer Table/Cosmos and generate Excel on demand.
- Consider ETag conditional writes for stricter concurrency (not yet implemented here for simplicity).

### Troubleshooting
- 404 on blob during lease acquire is normal when creating first file.
- Ensure container name is lowercase.
- If large file grows, consider archiving older rows to a new blob.
- SAS expired: regenerate SAS and update `EXCEL_SAS_URL`.
- Permission errors: confirm SAS includes `r` and `w` (read/write) at minimum.
