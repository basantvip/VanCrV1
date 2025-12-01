"""
VanCr Backend API - Contact Form Service
Python Flask app with Azure Cosmos DB (Managed Identity auth)
No secrets/keys in code - uses DefaultAzureCredential (Azure AD)
"""
import os
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential

app = Flask(__name__)
CORS(app)  # Enable CORS for all origins (restrict in production via CORS config)

# Environment variables (set in App Service Configuration)
COSMOS_ENDPOINT = os.environ.get('COSMOS_ENDPOINT')  # e.g. https://vancr-cosmos.documents.azure.com:443/
COSMOS_CONNECTION_STRING = os.environ.get('COSMOS_CONNECTION_STRING')  # For local testing
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'VanCrDB')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', 'ContactSubmissions')

# Initialize Cosmos client with Managed Identity or connection string
credential = DefaultAzureCredential()
cosmos_client = None
database = None
container = None

def init_cosmos():
    """Initialize Cosmos DB client, database, and container."""
    global cosmos_client, database, container
    
    # Use connection string for local dev, Managed Identity for production
    if COSMOS_CONNECTION_STRING:
        cosmos_client = CosmosClient.from_connection_string(COSMOS_CONNECTION_STRING)
    elif COSMOS_ENDPOINT:
        cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
    else:
        raise ValueError("COSMOS_ENDPOINT or COSMOS_CONNECTION_STRING environment variable is required")
    database = cosmos_client.create_database_if_not_exists(id=DATABASE_NAME)
    container = database.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/id")
        # No offer_throughput for serverless Cosmos DB
    )
    app.logger.info(f"Cosmos initialized: {DATABASE_NAME}/{CONTAINER_NAME}")

@app.route('/')
def index():
    return jsonify({
        'service': 'VanCr Contact API',
        'status': 'running',
        'database': DATABASE_NAME,
        'container': CONTAINER_NAME
    })

@app.route('/api/save-contact', methods=['POST'])
def save_contact():
    """Save contact form submission to Cosmos DB."""
    try:
        data = request.get_json(force=True) or {}
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        subject = data.get('subject', '').strip()
        
        if not message and not email:
            return jsonify({'ok': False, 'error': 'Missing message or email'}), 400
        
        # Create document
        doc_id = str(uuid.uuid4())
        document = {
            'id': doc_id,
            'phone': phone,
            'email': email,
            'message': message,
            'subject': subject,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'actionTaken': 'Pending',
            'type': 'contact_submission'
        }
        
        # Insert into Cosmos
        if container is None:
            init_cosmos()
        
        container.create_item(body=document)
        
        return jsonify({
            'ok': True,
            'id': doc_id,
            'database': DATABASE_NAME,
            'container': CONTAINER_NAME
        }), 200
        
    except Exception as e:
        app.logger.exception('save_contact error')
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        if container is None:
            init_cosmos()
        # Simple connectivity check
        list(container.query_items(
            query='SELECT TOP 1 * FROM c',
            enable_cross_partition_query=True
        ))
        return jsonify({'status': 'healthy', 'cosmos': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

if __name__ == '__main__':
    # Don't initialize Cosmos on startup in debug mode (causes double init)
    # It will initialize on first request instead
    
    # Local development server
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
