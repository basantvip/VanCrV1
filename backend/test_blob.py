"""Test Azure Blob Storage connection with Azure CLI credentials."""
from azure.identity import AzureCliCredential, ChainedTokenCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient
import sys

STORAGE_ACCOUNT = 'vancrstore'
STORAGE_ENDPOINT = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
CONTAINER_NAME = 'product-images'

try:
    print("1. Initializing Azure credential...")
    cli_credential = AzureCliCredential()
    managed_credential = ManagedIdentityCredential()
    credential = ChainedTokenCredential(cli_credential, managed_credential)
    print("   ✓ Credential initialized")
    
    print(f"\n2. Connecting to Blob Storage: {STORAGE_ENDPOINT}")
    blob_service_client = BlobServiceClient(account_url=STORAGE_ENDPOINT, credential=credential)
    print("   ✓ BlobServiceClient created")
    
    print(f"\n3. Checking container: {CONTAINER_NAME}")
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    
    # Try to list blobs (this tests read permission)
    print("   Attempting to list blobs...")
    blobs = list(container_client.list_blobs())
    print(f"   ✓ Found {len(blobs)} blobs in container")
    
    if blobs:
        print("\n   First 5 blobs:")
        for blob in blobs[:5]:
            print(f"   - {blob.name}")
    
    print("\n4. Testing write permission...")
    test_blob_name = "test-connection.txt"
    test_content = "Connection test from local development"
    
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=test_blob_name)
    blob_client.upload_blob(test_content, overwrite=True)
    print(f"   ✓ Successfully uploaded test blob: {test_blob_name}")
    
    # Delete test blob
    blob_client.delete_blob()
    print(f"   ✓ Successfully deleted test blob")
    
    print("\n✅ All tests passed! Blob storage is properly configured.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
