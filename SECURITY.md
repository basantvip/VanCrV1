# Security Configuration - Azure Key Vault

This application uses **Azure Key Vault** with **Managed Identity** to securely store and access secrets. No connection strings or keys are stored in the codebase.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Flask Backend  │────────>│  Key Vault       │────────>│  Secrets        │
│  (App Service)  │  RBAC   │  kv-vancr-prod   │         │  - Cosmos Conn  │
│                 │         │                  │         │  - Storage Conn │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │
        │ Managed Identity
        │
        v
┌─────────────────────────────────┐
│  Azure Resources                │
│  - Cosmos DB (vancr-cosmos)     │
│  - Storage (vancrstore)         │
└─────────────────────────────────┘
```

## Key Vault Setup

### 1. Key Vault Created
- **Name**: `kv-vancr-prod`
- **Resource Group**: `rg-vancr-prod`
- **Location**: `eastus`
- **RBAC**: Enabled (role-based access control)

### 2. Secrets Stored
- `CosmosConnectionString`: Cosmos DB connection string
- `StorageConnectionString`: Azure Storage connection string

### 3. Access Control
- **Your User**: `Key Vault Secrets Officer` role (for managing secrets)
- **App Service**: `Key Vault Secrets User` role (for reading secrets)

## Local Development

### Prerequisites
1. Install Azure CLI: https://aka.ms/azure-cli
2. Login to Azure: `az login`
3. Ensure you have `Key Vault Secrets Officer` role on the Key Vault

### Running Locally
The backend automatically retrieves secrets from Key Vault using your Azure CLI credentials (DefaultAzureCredential).

```powershell
# Option 1: Use the start script
.\backend\start-server.ps1

# Option 2: Set environment and run directly
$env:KEY_VAULT_NAME='kv-vancr-prod'
.\.venv\Scripts\python.exe backend\app.py
```

### How It Works
1. `DefaultAzureCredential` tries authentication methods in this order:
   - Environment variables (for production)
   - Managed Identity (for Azure App Service)
   - Azure CLI (for local development) ✓
   - Interactive browser login (fallback)

2. The backend connects to Key Vault using this credential
3. Secrets are retrieved at startup and used for Cosmos DB and Storage connections

## Production Deployment

### App Service Configuration
When deployed to Azure App Service, the app automatically uses its **Managed Identity** to access Key Vault.

Required App Service Settings:
```bash
KEY_VAULT_NAME=kv-vancr-prod
DATABASE_NAME=VanCrDB
CONTAINER_NAME=ContactSubmissions
```

### Managed Identity Setup
```bash
# Enable system-assigned managed identity
az webapp identity assign -n vancr-backend -g rg-vancr-prod

# Get the principal ID
PRINCIPAL_ID=$(az webapp identity show -n vancr-backend -g rg-vancr-prod --query principalId -o tsv)

# Grant Key Vault access
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $PRINCIPAL_ID \
  --scope /subscriptions/<sub-id>/resourceGroups/rg-vancr-prod/providers/Microsoft.KeyVault/vaults/kv-vancr-prod
```

## Security Benefits

✅ **No secrets in code**: Connection strings never appear in source code  
✅ **No secrets in Git**: Nothing sensitive to commit accidentally  
✅ **Audit trail**: Key Vault logs all secret access  
✅ **Rotation support**: Update secrets in one place, apps reload automatically  
✅ **RBAC**: Fine-grained access control per user/application  
✅ **Encryption**: Secrets encrypted at rest and in transit  

## Troubleshooting

### "Authentication failed" error
```
Solution: Run `az login` and ensure you have access to the Key Vault
```

### "Secret not found" error
```
Solution: Verify secrets exist:
az keyvault secret list --vault-name kv-vancr-prod -o table
```

### "Access denied" error
```
Solution: Check your role assignment:
az role assignment list --scope /subscriptions/<sub-id>/resourceGroups/rg-vancr-prod/providers/Microsoft.KeyVault/vaults/kv-vancr-prod --assignee <your-email> -o table
```

## Adding New Secrets

```bash
# Add a new secret
az keyvault secret set \
  --vault-name kv-vancr-prod \
  --name MyNewSecret \
  --value "secret-value"

# Update the backend code to retrieve it
# In backend/app.py:
MY_SECRET = get_secret('MyNewSecret')
```

## References
- [Azure Key Vault Documentation](https://docs.microsoft.com/azure/key-vault/)
- [DefaultAzureCredential](https://docs.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
- [Managed Identity Overview](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview)
