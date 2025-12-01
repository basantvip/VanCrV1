# VanCr Backend API

Python Flask backend for VanCr contact form using **Azure Cosmos DB** with **Managed Identity** authentication (no connection strings or keys in code).

## Architecture
- **Runtime**: Python 3.11+ on Azure App Service (Linux)
- **Database**: Azure Cosmos DB (SQL API)
- **Auth**: Azure AD Managed Identity (system-assigned)
- **Security**: No secrets in code; uses `DefaultAzureCredential`

## Endpoints
- `GET /` - Service info
- `POST /api/save-contact` - Save contact submission
  - Body: `{ "phone": "...", "email": "...", "message": "...", "subject": "..." }`
- `GET /health` - Health check (tests Cosmos connectivity)

## Local Development

### Prerequisites
- Python 3.11+
- Azure CLI installed and logged in (`az login`)
- Cosmos DB account with RBAC role assigned to your Azure user

### Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your Cosmos endpoint

# Run
python app.py
```

Test:
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/save-contact -Body (@{phone='123';email='test@example.com';message='Hello';subject='Test'} | ConvertTo-Json) -ContentType 'application/json'
```

## Azure Deployment

### 1. Provision Resources (Cloud Shell or CLI)
```bash
# Variables
RG=rg-vancr-prod
LOC=centralindia
COSMOS_ACCOUNT=vancr-cosmos
APP_NAME=vancr-backend
PLAN=vancr-plan

# Resource group
az group create -n $RG -l $LOC

# Cosmos DB account (serverless for low cost)
az cosmosdb create -n $COSMOS_ACCOUNT -g $RG --locations regionName=$LOC --kind GlobalDocumentDB --enable-free-tier false --server-version 4.0 --capabilities EnableServerless

# App Service Plan (Linux, Python)
az appservice plan create -n $PLAN -g $RG -l $LOC --is-linux --sku B1

# App Service (Python 3.11)
az webapp create -n $APP_NAME -g $RG -p $PLAN --runtime "PYTHON:3.11"

# Enable system-assigned managed identity
az webapp identity assign -n $APP_NAME -g $RG
```

### 2. Assign RBAC Role to Managed Identity
```bash
# Get managed identity principal ID
PRINCIPAL_ID=$(az webapp identity show -n $APP_NAME -g $RG --query principalId -o tsv)

# Get Cosmos account resource ID
COSMOS_ID=$(az cosmosdb show -n $COSMOS_ACCOUNT -g $RG --query id -o tsv)

# Assign Cosmos DB Data Contributor role (built-in role ID)
az role assignment create --assignee $PRINCIPAL_ID --role "Cosmos DB Account Reader Writer" --scope $COSMOS_ID

# Or use custom Cosmos DB Data Contributor role:
az cosmosdb sql role assignment create --account-name $COSMOS_ACCOUNT --resource-group $RG --role-definition-name "Cosmos DB Built-in Data Contributor" --principal-id $PRINCIPAL_ID --scope "/"
```

### 3. Configure App Settings
```bash
COSMOS_ENDPOINT=$(az cosmosdb show -n $COSMOS_ACCOUNT -g $RG --query documentEndpoint -o tsv)

az webapp config appsettings set -n $APP_NAME -g $RG --settings \
  COSMOS_ENDPOINT="$COSMOS_ENDPOINT" \
  DATABASE_NAME="VanCrDB" \
  CONTAINER_NAME="ContactSubmissions" \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

### 4. Configure Startup Command
```bash
az webapp config set -n $APP_NAME -g $RG --startup-file "startup.txt"
```

### 5. Deploy Code
```bash
cd backend
az webapp up -n $APP_NAME -g $RG --runtime "PYTHON:3.11" --logs
```

Or use GitHub Actions (see workflow below).

## GitHub Actions Deployment

Add workflow at `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend API

on:
  push:
    branches: [ main ]
    paths:
      - 'backend/**'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        working-directory: backend
        run: |
          pip install -r requirements.txt
      
      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v2
        with:
          app-name: vancr-backend
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
          package: backend
```

Add secret `AZURE_WEBAPP_PUBLISH_PROFILE` from Portal: App Service > Deployment Center > Download publish profile.

## CORS Configuration
In Portal > App Service > CORS, add your frontend domain or `*` for testing.

## Testing Deployment
```bash
curl -X POST https://vancr-backend.azurewebsites.net/api/save-contact \
  -H "Content-Type: application/json" \
  -d '{"phone":"123","email":"test@example.com","message":"Hello","subject":"Test"}'
```

## Monitoring
- Enable Application Insights in Portal > App Service > Application Insights
- View logs: `az webapp log tail -n vancr-backend -g rg-vancr-prod`

## Security Notes
- No connection strings or keys stored anywhere
- Managed Identity uses Azure AD token exchange
- Rotate nothing (keyless authentication)
- Least privilege: assign Cosmos roles at container level if needed
- Enable App Service authentication (Easy Auth) for additional security layer

## Cost Optimization
- Use Cosmos serverless (pay per request)
- Scale App Service plan as needed (B1 → F1 for dev/test)
- Monitor RU consumption in Cosmos metrics

## Troubleshooting
- **403 on Cosmos**: Verify role assignment propagated (takes ~5 min)
- **Identity not found**: Ensure system-assigned identity enabled
- **Local auth fails**: Run `az login` and ensure your user has Cosmos RBAC role
- **Container not found**: First POST creates database + container automatically
