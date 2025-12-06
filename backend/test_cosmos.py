from azure.cosmos import CosmosClient
import os

# Connect using master key from environment variable
COSMOS_KEY = os.environ.get('COSMOS_DB_KEY')
if not COSMOS_KEY:
    raise ValueError('COSMOS_DB_KEY environment variable not set')

client = CosmosClient(
    'https://vancr-cosmos.documents.azure.com:443/', 
    COSMOS_KEY
)

db = client.get_database_client('VanCrDB')
container = db.get_container_client('Products')

# Query all products
items = list(container.query_items(
    'SELECT * FROM c', 
    enable_cross_partition_query=True
))

print(f'Total products in Cosmos DB: {len(items)}')
print()

for i, product in enumerate(items[:5]):
    print(f"Product {i+1}:")
    print(f"  ID: {product.get('id', 'N/A')}")
    print(f"  Price: ₹{product.get('price', 'N/A')}")
    print(f"  Categories: {product.get('categories', [])}")
    print()
