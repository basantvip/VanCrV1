# VanCr Deployment Guide - Python Backend + Cosmos DB

Complete step-by-step guide to deploy the VanCr contact form backend.

## Quick Overview
- **Backend**: Python Flask on Azure App Service (Linux)
- **Database**: Azure Cosmos DB (serverless, SQL API)
- **Authentication**: Managed Identity (no keys/secrets)
- **Deployment**: GitHub Actions or Azure CLI

## Prerequisites
- Azure subscription
- Azure CLI installed (`az --version`)
- Git repository connected to GitHub

## Step 1: Azure Login
```bash
az login
az account set --subscription "<your-subscription-id>"
```

## Step 2: Provision Infrastructure

### Copy and run this complete script in Cloud Shell or local terminal:

```bash
#!/bin/bash
# VanCr Infrastructure Setup

# Configuration
RG=rg-vancr-prod
LOC=centralindia
COSMOS_ACCOUNT=vancr-cosmos
APP_NAME=vancr-backend
PLAN=vancr-plan

echo "Creating resource group..."
az group create -n $RG -l $LOC

echo "Creating Cosmos DB account (serverless)..."
az cosmosdb create \
  -n $COSMOS_ACCOUNT \
  -g $RG \
  --locations regionName=$LOC \
  --kind GlobalDocumentDB \
  --capabilities EnableServerless \
  --default-consistency-level Session

echo "Creating App Service Plan (B1 Linux)..."
az appservice plan create \
  -n $PLAN \
  -g $RG \
  -l $LOC \
  --is-linux \
  --sku B1

echo "Creating Web App (Python 3.11)..."
az webapp create \
  -n $APP_NAME \
  -g $RG \
  -p $PLAN \
  --runtime "PYTHON:3.11"

echo "Enabling managed identity..."
az webapp identity assign -n $APP_NAME -g $RG

echo "Getting identity principal ID..."
PRINCIPAL_ID=$(az webapp identity show -n $APP_NAME -g $RG --query principalId -o tsv)
echo "Principal ID: $PRINCIPAL_ID"

echo "Assigning Cosmos DB role (wait 5 min for propagation)..."
az cosmosdb sql role assignment create \
  --account-name $COSMOS_ACCOUNT \
  --resource-group $RG \
  --role-definition-name "Cosmos DB Built-in Data Contributor" \
  --principal-id $PRINCIPAL_ID \
  --scope "/"

echo "Configuring app settings..."
COSMOS_ENDPOINT=$(az cosmosdb show -n $COSMOS_ACCOUNT -g $RG --query documentEndpoint -o tsv)

az webapp config appsettings set \
  -n $APP_NAME \
  -g $RG \
  --settings \
    COSMOS_ENDPOINT="$COSMOS_ENDPOINT" \
    DATABASE_NAME="VanCrDB" \
    CONTAINER_NAME="ContactSubmissions" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true

echo "Setting startup command..."
az webapp config set -n $APP_NAME -g $RG --startup-file "startup.txt"

echo "Enabling CORS (allow all origins for testing)..."
az webapp cors add -n $APP_NAME -g $RG --allowed-origins '*'

echo ""
echo "✅ Infrastructure provisioned!"
echo "App URL: https://$APP_NAME.azurewebsites.net"
echo "Next: Deploy code via GitHub Actions or CLI"
```

## Step 3: Deploy Code

### Option A: GitHub Actions (Recommended)

1. **Get publish profile:**
   ```bash
   az webapp deployment list-publishing-profiles -n vancr-backend -g rg-vancr-prod --xml
   ```

2. **Add GitHub secret:**
   - Go to GitHub repo → Settings → Secrets and variables → Actions
   - Add secret: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Paste the XML content

3. **Push to trigger deployment:**
   ```bash
   git add .
   git commit -m "Add Python backend with Cosmos DB"
   git push origin main
   ```

### Option B: Azure CLI Direct Deploy

```bash
cd backend
az webapp up -n vancr-backend -g rg-vancr-prod --runtime "PYTHON:3.11" --logs
```

## Step 4: Verify Deployment

```bash
# Health check
curl https://vancr-backend.azurewebsites.net/health

# Test submission
curl -X POST https://vancr-backend.azurewebsites.net/api/save-contact \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","email":"test@example.com","message":"Test message","subject":"Test"}'

# Expected response:
# {"ok":true,"id":"<uuid>","database":"VanCrDB","container":"ContactSubmissions"}
```

## Step 5: Update Frontend

Uncomment and update in `contact.html`:
```html
<script>
window.EMAIL_ENDPOINT = 'https://vancr-backend.azurewebsites.net/api/save-contact';
</script>
```

Commit and push:
```bash
git add contact.html
git commit -m "Connect frontend to backend API"
git push origin main
```

## Step 6: Verify in Cosmos DB

1. Portal → Cosmos DB account → Data Explorer
2. Navigate: VanCrDB → ContactSubmissions → Items
3. View submitted contact entries

## Local Development

```bash
# Login to Azure (for local Managed Identity simulation)
az login

# Setup Python environment
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Cosmos endpoint from:
az cosmosdb show -n vancr-cosmos -g rg-vancr-prod --query documentEndpoint -o tsv

# Assign your user Cosmos role (one-time)
MY_USER_ID=$(az ad signed-in-user show --query id -o tsv)
az cosmosdb sql role assignment create \
  --account-name vancr-cosmos \
  --resource-group rg-vancr-prod \
  --role-definition-name "Cosmos DB Built-in Data Contributor" \
  --principal-id $MY_USER_ID \
  --scope "/"

# Run locally
python app.py

# Test
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/save-contact `
  -Body (@{phone='123';email='dev@example.com';message='Local test';subject='Dev'} | ConvertTo-Json) `
  -ContentType 'application/json'
```

## Monitoring & Logs

```bash
# Tail logs
az webapp log tail -n vancr-backend -g rg-vancr-prod

# Enable Application Insights (recommended)
az monitor app-insights component create \
  -a vancr-backend-insights \
  -l centralindia \
  -g rg-vancr-prod \
  --application-type web

# Link to App Service
INSIGHTS_KEY=$(az monitor app-insights component show -a vancr-backend-insights -g rg-vancr-prod --query instrumentationKey -o tsv)
az webapp config appsettings set -n vancr-backend -g rg-vancr-prod --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSIGHTS_KEY
```

## Troubleshooting

### 403 Forbidden on Cosmos
- Wait 5-10 minutes for role assignment propagation
- Verify role: Portal → Cosmos → Access Control (IAM) → Role assignments
- Check principal ID matches: `az webapp identity show -n vancr-backend -g rg-vancr-prod`

### App won't start
- Check logs: `az webapp log tail -n vancr-backend -g rg-vancr-prod`
- Verify startup command: Portal → Configuration → General settings → Startup Command
- Ensure `startup.txt` exists in repo

### CORS errors
- Add frontend domain: Portal → App Service → CORS
- Or CLI: `az webapp cors add -n vancr-backend -g rg-vancr-prod --allowed-origins 'https://vancr.in'`

### Local DefaultAzureCredential fails
- Run `az login`
- Ensure your user has Cosmos RBAC role (see local dev section)
- Check: `az account show`

## Cost Estimation
- **Cosmos DB Serverless**: ~$0.25 per million read requests, ~$1.25 per million writes
- **App Service B1**: ~$13/month (or F1 free tier for dev)
- **Total for low traffic**: < $15/month

## Security Checklist
- ✅ No secrets in code (Managed Identity)
- ✅ HTTPS only (automatic on App Service)
- ✅ CORS configured (restrict to production domain)
- ✅ Least privilege (Cosmos RBAC at database level)
- ⚠️ Add rate limiting (consider Azure Front Door or API Management later)
- ⚠️ Enable Easy Auth for admin endpoints (future)

## Next Steps
- Set up custom domain with SSL
- Add email notifications via Azure Communication Services or SendGrid
- Implement rate limiting
- Add Power BI or Azure Monitor dashboards for submissions
- Archive old submissions to cheaper blob storage
