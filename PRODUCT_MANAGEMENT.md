# Product Management Feature - Complete Guide

## Overview
This feature allows you to upload product images to Azure Blob Storage and manage product metadata in Cosmos DB. Products are displayed in the catalog with advanced filtering.

## What's Implemented

### ✅ Frontend
- **add-product.html**: Product upload form with:
  - Item name input
  - Image upload with preview
  - Multi-select checkboxes for:
    - Categories: Girls, Boys, Baby, Accessories, Footwear
    - Age Groups: Newborn, Infant, Toddler, Preschool, Kids
    - Seasons: Spring, Summer, Fall, Winter, All Season
    - Occasions: Casual, Formal, Party, Traditional, Everyday
  - Client-side validation
  - Success/error message display

- **catalog.html**: Updated to fetch and display products from backend with:
  - Filter dropdowns for category, age group, season, occasion
  - Search by item name
  - Product grid with images from Azure Blob Storage
  - Category and age group tags on each product card

### ✅ Backend (app.py)
- **POST /api/add-product**: 
  - Accepts multipart/form-data
  - Validates file type (PNG, JPG, JPEG, GIF, WEBP)
  - Generates unique UUID for each product
  - Uploads image to Azure Blob Storage (`product-images` container)
  - Saves metadata to Cosmos DB (`Products` container)
  - Auto-creates containers if they don't exist
  - Returns product details with public image URL

- **GET /api/products**:
  - Supports query parameters: category, ageGroup, season, occasion
  - Uses Cosmos DB `ARRAY_CONTAINS` for multi-value filtering
  - Returns filtered products sorted by creation date (newest first)

### ✅ Azure Infrastructure
- **Storage Account**: `vancrstore` (Standard_LRS, Hot tier)
  - Container: `product-images` (public blob access)
  - Location: East US
  
- **Cosmos DB**: `vancr-cosmos` (serverless)
  - Database: `VanCrDB`
  - Container: `Products` (auto-created on first product upload)
  - Partition key: `/id`

## How to Use

### 1. Start Backend Server

**Option A: PowerShell Script (Recommended)**
```powershell
cd C:\Users\bagrawal\OneDrive\VanCrV1\backend
.\start-server.ps1
```

**Option B: Manual Command**
```powershell
# Backend uses Azure Key Vault for secrets
cd C:\Users\bagrawal\OneDrive\VanCrV1\backend
$env:KEY_VAULT_NAME='kv-vancr-prod'
C:\Users\bagrawal\OneDrive\VanCrV1\.venv\Scripts\python.exe app.py
```

Server will start on **http://localhost:8000**

**Note**: You must be logged in with Azure CLI (`az login`) for local development. The backend retrieves connection strings from Azure Key Vault.

### 2. Start Frontend Server

Open a new terminal:
```powershell
cd C:\Users\bagrawal\OneDrive\VanCrV1
python -m http.server 8080
```

Frontend will be available at **http://localhost:8080**

### 3. Add Products

1. Navigate to http://localhost:8080/add-product.html
2. Fill in:
   - Item name (e.g., "Girl's Summer Dress")
   - Upload image
   - Select at least one category
   - Select at least one age group
   - Optionally select seasons and occasions
3. Click "Upload Product"
4. Success message will show the product was added

### 4. View Products in Catalog

1. Navigate to http://localhost:8080/catalog.html
2. Use filter dropdowns to filter by:
   - Category (Girls, Boys, etc.)
   - Age Group (Newborn, Infant, etc.)
   - Season
   - Occasion
3. Use search box to filter by name
4. Products will display with images from Azure Blob Storage

## Testing the API Directly

### Add a Product
```powershell
# Create test image file first
Add-Content -Path test-product.jpg -Value "test" -Encoding Byte

# Upload product
$form = @{
    itemName = 'Test Baby Onesie'
    itemImage = Get-Item -Path test-product.jpg
    categories = '["Baby"]'
    ageGroups = '["Newborn","Infant"]'
    seasons = '["All Season"]'
    occasions = '["Casual","Everyday"]'
}

Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/add-product -Form $form
```

### Get All Products
```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:8000/api/products | ConvertTo-Json -Depth 5
```

### Get Filtered Products
```powershell
# Products for Girls
Invoke-RestMethod -Method Get -Uri 'http://localhost:8000/api/products?category=Girls'

# Products for Toddlers in Summer
Invoke-RestMethod -Method Get -Uri 'http://localhost:8000/api/products?ageGroup=Toddler&season=Summer'
```

## Database Schema

### Products Container
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "itemName": "Girl's Summer Dress",
  "imageUrl": "https://vancrstore.blob.core.windows.net/product-images/products/550e8400-e29b-41d4-a716-446655440000.jpg",
  "categories": ["Girls"],
  "ageGroups": ["Toddler", "Preschool"],
  "seasons": ["Spring", "Summer"],
  "occasions": ["Casual", "Party"],
  "createdAt": "2025-12-01T12:34:56.789Z",
  "type": "product"
}
```

## Deployment to Azure

### Update App Service Configuration

Add storage connection string to your App Service:

```bash
STORAGE_CONN=$(az storage account show-connection-string -n vancrstore -g rg-vancr-prod --query connectionString -o tsv)

az webapp config appsettings set \
  -n vancr-backend \
  -g rg-vancr-prod \
  --settings STORAGE_CONNECTION_STRING="$STORAGE_CONN"
```

### Deploy Backend

```bash
cd backend
az webapp up -n vancr-backend -g rg-vancr-prod --runtime "PYTHON:3.11"
```

### Update Frontend URLs

After deployment, update `catalog.html` and `add-product.html`:

Change:
```javascript
const API_BASE = 'http://localhost:8000';
```

To:
```javascript
const API_BASE = 'https://vancr-backend.azurewebsites.net';
```

## Security Notes

- **Storage Account**: `vancrstore` has public blob access enabled for product images
- **Cosmos DB**: Uses connection string for local dev, managed identity in production
- **CORS**: Enabled for all origins (restrict to your domain in production)
- **File Upload**: Limited to 5 common image formats, validated on backend
- **Authentication**: Currently no authentication on upload endpoint (add admin auth in production)

## Troubleshooting

### Backend won't start
- Ensure virtual environment is activated
- Check connection strings are set correctly
- Verify azure-storage-blob package is installed: `pip list | Select-String azure-storage-blob`

### Images not uploading
- Check storage connection string is correct
- Verify `vancrstore` storage account exists
- Check file size (default Flask limit is 16MB)

### Products not displaying in catalog
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS is enabled on backend
- Test API directly: `http://localhost:8000/api/products`

### Container creation fails
- Check Cosmos DB connection string
- Verify account has permissions
- Check Azure portal → Cosmos DB → Data Explorer for containers

## Next Steps

1. **Add Authentication**: Protect `/api/add-product` endpoint with admin authentication
2. **Image Optimization**: Resize images before upload, create thumbnails
3. **Price Field**: Add price to products for e-commerce functionality
4. **Inventory Management**: Track stock quantities
5. **Product Editing**: Add ability to update/delete existing products
6. **Categories from Database**: Store categories in Cosmos DB instead of hardcoding
7. **Advanced Filters**: Add price range, rating, availability filters
8. **Pagination**: Implement pagination for large product catalogs
9. **CDN**: Add Azure CDN in front of blob storage for better performance
10. **Image Validation**: Validate image dimensions and quality

## Files Modified/Created

- ✅ `add-product.html` - Product upload form
- ✅ `catalog.html` - Updated with backend integration
- ✅ `backend/app.py` - Added product endpoints
- ✅ `backend/requirements.txt` - Added azure-storage-blob
- ✅ `backend/start-server.ps1` - Server startup script
- ✅ `backend/.env.example` - Updated with storage config
- ✅ `DEPLOYMENT.md` - Updated provisioning script
- ✅ `PRODUCT_MANAGEMENT.md` - This guide

## Support

For issues or questions about this feature, check:
1. Backend logs in terminal
2. Browser developer console (F12)
3. Azure portal → Storage Account → Containers
4. Azure portal → Cosmos DB → Data Explorer → VanCrDB → Products
