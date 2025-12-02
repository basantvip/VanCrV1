"""
VanCr Backend API - Contact Form & Product Management Service
Python Flask app with Azure Cosmos DB, Azure Blob Storage, and Azure SQL Database
Uses Azure Key Vault with Managed Identity for secure secret management
"""
import os
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.keyvault.secrets import SecretClient
from werkzeug.utils import secure_filename
import pyodbc
import bcrypt

# Flask app with static files from parent directory
app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)  # Enable CORS for all origins (restrict in production via CORS config)

# Environment variables
KEY_VAULT_NAME = os.environ.get('KEY_VAULT_NAME', 'kv-vancr-prod')
KEY_VAULT_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net/"
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'VanCrDB')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', 'ContactSubmissions')
PRODUCTS_CONTAINER = 'Products'
SQL_SERVER = 'vancrsql2025.database.windows.net'
SQL_DATABASE = 'VanCr'
SQL_USERNAME = 'vancradmin'
BLOB_CONTAINER = 'product-images'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize Azure credentials and Key Vault client
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KEY_VAULT_URI, credential=credential)

# Retrieve secrets from Key Vault
def get_secret(secret_name):
    """Retrieve secret from Azure Key Vault."""
    try:
        print(f"Retrieving secret '{secret_name}' from Key Vault: {KEY_VAULT_URI}")
        secret = secret_client.get_secret(secret_name)
        print(f"Successfully retrieved secret '{secret_name}'")
        return secret.value
    except Exception as e:
        print(f"ERROR retrieving secret {secret_name}: {e}")
        import traceback
        traceback.print_exc()
        raise

# Get connection strings from Key Vault
print("Initializing connection strings from Key Vault...")
COSMOS_CONNECTION_STRING = get_secret('CosmosConnectionString')
STORAGE_CONNECTION_STRING = get_secret('StorageConnectionString')
SQL_PASSWORD = get_secret('SqlPassword')  # Store SQL password in Key Vault
print("Connection strings retrieved successfully")

cosmos_client = None
database = None
container = None

def init_cosmos():
    """Initialize Cosmos DB client, database, and container."""
    global cosmos_client, database, container
    
    if not COSMOS_CONNECTION_STRING:
        raise ValueError("Could not retrieve Cosmos DB connection string from Key Vault")
    
    cosmos_client = CosmosClient.from_connection_string(COSMOS_CONNECTION_STRING)
    database = cosmos_client.create_database_if_not_exists(id=DATABASE_NAME)
    container = database.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/id")
        # No offer_throughput for serverless Cosmos DB
    )
    app.logger.info(f"Cosmos initialized: {DATABASE_NAME}/{CONTAINER_NAME}")

def get_sql_connection():
    """Get SQL Server connection."""
    try:
        # Use SQL_PASSWORD from Key Vault if available, otherwise fallback
        password = SQL_PASSWORD if SQL_PASSWORD else 'VanCr@2025SecurePass!'
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={password}"
        )
        return pyodbc.connect(connection_string)
    except Exception as e:
        app.logger.error(f"SQL connection error: {e}")
        raise

@app.route('/')
def index():
    """Serve the home page."""
    try:
        return send_from_directory(os.path.join(os.path.dirname(__file__), '..'), 'index.html')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (HTML, CSS, JS, images)."""
    try:
        # Don't serve API routes as static files
        if filename.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404
        return send_from_directory(os.path.join(os.path.dirname(__file__), '..'), filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/')
def api_index():
    """API status endpoint."""
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

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/add-product', methods=['POST'])
def add_product():
    """Add product with image upload to Azure Blob Storage and metadata to Cosmos DB."""
    try:
        # Check authorization - only Admin users can add products
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'ok': False, 'error': 'Unauthorized. Please login.'}), 401
        
        # Verify user is Admin
        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_level FROM Users WHERE user_id = ? AND active = 1", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or row[0] != 'Admin':
            return jsonify({'ok': False, 'error': 'Unauthorized. Admin access required.'}), 403
        
        # Validate form data
        if 'itemImage' not in request.files:
            return jsonify({'ok': False, 'error': 'No image file provided'}), 400
        
        file = request.files['itemImage']
        if file.filename == '':
            return jsonify({'ok': False, 'error': 'No image selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'ok': False, 'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
        
        # Validate price
        price = request.form.get('price', '').strip()
        if not price:
            return jsonify({'ok': False, 'error': 'Price is required'}), 400
        
        try:
            price = float(price)
            if price < 0:
                return jsonify({'ok': False, 'error': 'Price cannot be negative'}), 400
        except ValueError:
            return jsonify({'ok': False, 'error': 'Invalid price format'}), 400
        
        # Parse JSON arrays
        import json
        categories = json.loads(request.form.get('categories', '[]'))
        age_groups = json.loads(request.form.get('ageGroups', '[]'))
        seasons = json.loads(request.form.get('seasons', '[]'))
        occasions = json.loads(request.form.get('occasions', '[]'))
        
        if not categories or not age_groups:
            return jsonify({'ok': False, 'error': 'At least one category and age group required'}), 400
        
        # Generate unique item ID
        item_id = str(uuid.uuid4())
        
        # Upload image to Azure Blob Storage
        if not STORAGE_CONNECTION_STRING:
            return jsonify({'ok': False, 'error': 'Storage not configured'}), 500
        
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER)
        
        # Create container if doesn't exist
        try:
            container_client.create_container(public_access='blob')
        except Exception:
            pass  # Container already exists
        
        # Secure filename and create blob name
        file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        blob_name = f"products/{item_id}.{file_ext}"
        
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file, overwrite=True)
        
        # Get public URL
        image_url = blob_client.url
        
        # Initialize Cosmos if needed
        if database is None:
            init_cosmos()
        
        # Ensure Products container exists
        products_container = database.create_container_if_not_exists(
            id=PRODUCTS_CONTAINER,
            partition_key=PartitionKey(path="/id")
        )
        
        # Create product document
        product_doc = {
            'id': item_id,
            'price': price,
            'imageUrl': image_url,
            'categories': categories,
            'ageGroups': age_groups,
            'seasons': seasons,
            'occasions': occasions,
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'type': 'product'
        }
        
        products_container.create_item(body=product_doc)
        
        return jsonify({
            'ok': True,
            'itemId': item_id,
            'price': price,
            'imageUrl': image_url
        }), 200
        
    except Exception as e:
        app.logger.exception('add_product error')
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get products with optional filters."""
    try:
        if database is None:
            init_cosmos()
        
        # Check if Products container exists
        try:
            products_container = database.get_container_client(PRODUCTS_CONTAINER)
        except Exception:
            return jsonify({'ok': True, 'products': []}), 200
        
        # Build query based on filters
        category = request.args.get('category')
        age_group = request.args.get('ageGroup')
        season = request.args.get('season')
        occasion = request.args.get('occasion')
        
        # Base query
        query = "SELECT * FROM c WHERE c.type = 'product'"
        
        # Add filters (Cosmos SQL supports ARRAY_CONTAINS)
        if category:
            query += f" AND ARRAY_CONTAINS(c.categories, '{category}')"
        if age_group:
            query += f" AND ARRAY_CONTAINS(c.ageGroups, '{age_group}')"
        if season:
            query += f" AND ARRAY_CONTAINS(c.seasons, '{season}')"
        if occasion:
            query += f" AND ARRAY_CONTAINS(c.occasions, '{occasion}')"
        
        query += " ORDER BY c.createdAt DESC"
        
        items = list(products_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        return jsonify({'ok': True, 'products': items}), 200
        
    except Exception as e:
        app.logger.exception('get_products error')
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product by ID - Admin only."""
    try:
        # Check authorization - only Admin users can delete products
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'ok': False, 'error': 'Unauthorized. Please login.'}), 401
        
        # Verify user is Admin
        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_level FROM Users WHERE user_id = ? AND active = 1", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or row[0] != 'Admin':
            return jsonify({'ok': False, 'error': 'Unauthorized. Admin access required.'}), 403
        
        if database is None:
            init_cosmos()
        
        products_container = database.get_container_client(PRODUCTS_CONTAINER)
        
        # Delete the product
        products_container.delete_item(item=product_id, partition_key=product_id)
        
        return jsonify({'ok': True, 'message': f'Product {product_id} deleted'}), 200
        
    except Exception as e:
        app.logger.exception('delete_product error')
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """Update a product - Admin only."""
    try:
        # Check authorization - only Admin users can update products
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'ok': False, 'error': 'Unauthorized. Please login.'}), 401
        
        # Verify user is Admin
        conn = get_sql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT access_level FROM Users WHERE user_id = ? AND active = 1", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or row[0] != 'Admin':
            return jsonify({'ok': False, 'error': 'Unauthorized. Admin access required.'}), 403
        
        data = request.get_json(force=True) or {}
        
        if database is None:
            init_cosmos()
        
        products_container = database.get_container_client(PRODUCTS_CONTAINER)
        
        # Get existing product
        existing_product = products_container.read_item(item=product_id, partition_key=product_id)
        
        # Update fields if provided
        if 'price' in data:
            existing_product['price'] = float(data['price'])
        if 'categories' in data:
            existing_product['categories'] = data['categories']
        if 'ageGroups' in data:
            existing_product['ageGroups'] = data['ageGroups']
        if 'seasons' in data:
            existing_product['seasons'] = data['seasons']
        if 'occasions' in data:
            existing_product['occasions'] = data['occasions']
        
        existing_product['updatedAt'] = datetime.now(timezone.utc).isoformat()
        
        # Update the product
        products_container.replace_item(item=product_id, body=existing_product)
        
        return jsonify({'ok': True, 'message': 'Product updated successfully', 'product': existing_product}), 200
        
    except Exception as e:
        app.logger.exception('update_product error')
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    """Create new user account with hashed password."""
    try:
        data = request.get_json(force=True) or {}
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip() if data.get('phone') else None
        password = data.get('password', '')
        
        # Validate required fields
        if not all([first_name, last_name, email, password]):
            return jsonify({'ok': False, 'error': 'Missing required fields'}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user in SQL database
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        try:
            # Generate new user ID
            user_id = str(uuid.uuid4())
            
            # Insert user
            cursor.execute("""
                INSERT INTO Users (user_id, email, first_name, last_name, phone, active, access_level)
                VALUES (?, ?, ?, ?, ?, 1, 'Standard')
            """, (user_id, email, first_name, last_name, phone))
            
            # Insert credentials
            cursor.execute("""
                INSERT INTO User_Credentials (user_id, password_hash)
                VALUES (?, ?)
            """, (user_id, password_hash))
            
            conn.commit()
            
            return jsonify({
                'ok': True,
                'userId': user_id,
                'message': 'Account created successfully'
            }), 201
            
        except pyodbc.IntegrityError as e:
            conn.rollback()
            if 'email' in str(e).lower():
                return jsonify({'ok': False, 'error': 'Email already exists'}), 400
            elif 'phone' in str(e).lower():
                return jsonify({'ok': False, 'error': 'Phone number already exists'}), 400
            else:
                return jsonify({'ok': False, 'error': 'User already exists'}), 400
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        app.logger.exception('signup error')
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user with email and password."""
    try:
        data = request.get_json(force=True) or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'ok': False, 'error': 'Email and password required'}), 400
        
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        try:
            # Get user and credentials
            cursor.execute("""
                SELECT u.user_id, u.email, u.first_name, u.last_name, u.active, u.access_level,
                       uc.password_hash, uc.failed_login_count
                FROM Users u
                INNER JOIN User_Credentials uc ON u.user_id = uc.user_id
                WHERE u.email = ? AND u.deleted_at IS NULL
            """, (email,))
            
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'ok': False, 'error': 'Invalid email or password'}), 401
            
            user_id, email, first_name, last_name, active, access_level, password_hash, failed_login_count = row
            
            # Check if account is active
            if not active:
                return jsonify({'ok': False, 'error': 'Account is inactive'}), 403
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                # Increment failed login count
                cursor.execute("""
                    UPDATE User_Credentials
                    SET failed_login_count = failed_login_count + 1
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                
                return jsonify({'ok': False, 'error': 'Invalid email or password'}), 401
            
            # Successful login - update last login and reset failed attempts
            cursor.execute("""
                UPDATE User_Credentials
                SET last_login_at = GETUTCDATE(), failed_login_count = 0
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            
            return jsonify({
                'ok': True,
                'userId': user_id,
                'email': email,
                'firstName': first_name,
                'lastName': last_name,
                'accessLevel': access_level,
                'message': 'Login successful'
            }), 200
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        app.logger.exception('login error')
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Don't initialize Cosmos on startup in debug mode (causes double init)
    # It will initialize on first request instead
    
    # Local development server
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)

