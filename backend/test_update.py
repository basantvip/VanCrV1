"""Test product update with image upload."""
import requests
import io

# Configuration
API_BASE = "http://localhost:8000"
PRODUCT_ID = "0d9b73e0-79b1-44a1-8258-8fc38c6c7cd5"
USER_ID = "test-admin-user"

# Create a fake image file
fake_image = io.BytesIO(b"fake image content for testing")
fake_image.name = "test-image.png"

# Prepare form data
files = {
    'itemImage': ('test-product.png', fake_image, 'image/png')
}

data = {
    'price': '399',
    'categories': '["Boys"]',
    'ageGroups': '["3-6 Months"]',
    'seasons': '["Summer"]',
    'occasions': '["Casual"]'
}

headers = {
    'X-User-Id': USER_ID
}

print(f"Updating product {PRODUCT_ID}...")
print(f"API: {API_BASE}/api/products/{PRODUCT_ID}")

try:
    response = requests.put(
        f"{API_BASE}/api/products/{PRODUCT_ID}",
        files=files,
        data=data,
        headers=headers
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.ok:
        result = response.json()
        if result.get('ok'):
            print("\n✓ Product updated successfully!")
            if 'product' in result:
                print(f"  New image URL: {result['product'].get('imageUrl')}")
        else:
            print(f"\n✗ Update failed: {result.get('error')}")
    else:
        print(f"\n✗ HTTP Error: {response.status_code}")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
