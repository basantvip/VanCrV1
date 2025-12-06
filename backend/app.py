"""
VanCr Backend API - Contact Form & Product Management Service
Python Flask app with Azure Cosmos DB, Azure Blob Storage, and Azure SQL Database
Uses Managed Identity for authentication to Azure services
"""
import os
import sys
import uuid
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
from flask_cors import CORS
import struct
from werkzeug.utils import secure_filename
import bcrypt

# Import Azure SDK with graceful fallback for local dev
try:
    from azure.cosmos import CosmosClient, PartitionKey
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings
    AZURE_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Azure SDK not available: {e}")
    print("Running in local dev mode without Azure services")
    AZURE_AVAILABLE = False

# Try to import pyodbc for SQL Server, fallback if not available
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    print("WARNING: pyodbc not available - SQL Server connections will fail")
    PYODBC_AVAILABLE = False

# Flask app with static files from parent directory
app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)  # Enable CORS for all origins (restrict in production via CORS config)

# Environment variables
COSMOS_ACCOUNT = os.environ.get('COSMOS_ACCOUNT', 'vancr-cosmos')
COSMOS_ENDPOINT = f"https://{COSMOS_ACCOUNT}.documents.azure.com:443/"
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'VanCrDB')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', 'ContactSubmissions')
PRODUCTS_CONTAINER = 'Products'

STORAGE_ACCOUNT = os.environ.get('STORAGE_ACCOUNT', 'vancrstore')
STORAGE_ENDPOINT = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
BLOB_CONTAINER = 'product-images'

SQL_SERVER = 'vancrsql2025.database.windows.net'
SQL_DATABASE = 'VanCr'
SQL_USERNAME = 'vancradmin'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize Azure credential for authentication
credential = None
if AZURE_AVAILABLE:
    print("Initializing Azure credential...")
    try:
        # For local development, use AzureCliCredential (works with 'az login')
        # For production (Azure), use ManagedIdentityCredential
        from azure.identity import AzureCliCredential, ManagedIdentityCredential, ChainedTokenCredential
        
        # Try CLI credential first (local), then Managed Identity (Azure)
        cli_credential = AzureCliCredential()
        managed_credential = ManagedIdentityCredential()
        credential = ChainedTokenCredential(cli_credential, managed_credential)
        
        print("[OK] Azure credential initialized (CLI + Managed Identity chain)")
    except Exception as e:
        print(f"WARNING: Could not initialize Azure credential: {e}")
        credential = None
else:
    print("WARNING: Azure SDK not available - Azure services will not work")

cosmos_client = None
database = None
container = None
blob_service_client = None

def init_cosmos():
    """Initialize Cosmos DB client using Managed Identity."""
    global cosmos_client, database, container
    
    if not credential:
        raise ValueError("Azure credential not initialized")
    
    print(f"Connecting to Cosmos DB: {COSMOS_ENDPOINT}")
    cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
    
    # Get existing database and container (don't try to create - requires different permissions)
    database = cosmos_client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)
    
    print(f"[OK] Cosmos DB initialized: {DATABASE_NAME}/{CONTAINER_NAME}")

def init_blob_storage():
    """Initialize Blob Storage client using Managed Identity."""
    global blob_service_client
    
    if not credential:
        raise ValueError("Azure credential not initialized")
    
    print(f"Connecting to Blob Storage: {STORAGE_ENDPOINT}")
    blob_service_client = BlobServiceClient(account_url=STORAGE_ENDPOINT, credential=credential)
    print(f"[OK] Blob Storage initialized")

def get_sql_connection():
    """Get SQL Server connection using Managed Identity (Azure AD authentication)."""
    try:
        if not credential:
            raise ValueError("Azure credential not initialized")
        
        # Get access token for SQL
        token = credential.get_token("https://database.windows.net/.default")
        token_bytes = token.token.encode("UTF-16-LE")
        token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        
        # Select an available ODBC driver on this host (prefer 18, then 17, then generic)
        available_drivers = [d for d in pyodbc.drivers()]
        app.logger.info(f"Available ODBC drivers: {available_drivers}")
        preferred = None
        for name in ('ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'SQL Server'):
            if name in available_drivers:
                preferred = name
                break
        if not preferred:
            app.logger.error('No suitable ODBC driver found on system drivers list')
            raise Exception('No suitable ODBC driver found. Please install Microsoft ODBC Driver for SQL Server.')

        driver_token = f"{{{preferred}}}"

        connection_string = (
            f"DRIVER={driver_token};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
        )

        SQL_COPT_SS_ACCESS_TOKEN = 1256  # Connection option for access token
        app.logger.info(f"Attempting Managed Identity SQL connection using driver: {preferred}")
        conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        print("[OK] SQL connection established with Managed Identity")
        return conn
    except Exception as e:
        app.logger.error(f"SQL Managed Identity connection failed: {e}")
        app.logger.error(f"SQL Managed Identity connection failed (outer): {e}")
        # Fallback to SQL authentication if Managed Identity fails
        password = os.environ.get('SQL_PASSWORD', 'VanCr@2025SecurePass!')
        # Fallback to SQL authentication: pick an available driver similarly
        available_drivers = [d for d in pyodbc.drivers()]
        # Fallback: pick an available driver for SQL auth too and log the choice
        fallback_drivers = [d for d in pyodbc.drivers()]
        app.logger.info(f"Drivers available for fallback: {fallback_drivers}")
        preferred = None
        for name in ('ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'SQL Server'):
            if name in available_drivers:
                preferred = name
                break
        if not preferred:
            raise Exception('No suitable ODBC driver found for fallback SQL auth. Install Microsoft ODBC Driver for SQL Server.')

        driver_token = f"{{{preferred}}}"

        connection_string = (
            f"DRIVER={driver_token};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )
        print("WARNING: Falling back to SQL authentication")
        return pyodbc.connect(connection_string)

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
    """Save contact form submission to SQL Database."""
    try:
        data = request.get_json(force=True) or {}
        phone = data.get('phone', '').strip() if data.get('phone') else None
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()
        subject = data.get('subject', '').strip() if data.get('subject') else None
        
        if not message and not email:
            return jsonify({'ok': False, 'error': 'Missing message or email'}), 400
        
        # Generate submission ID
        submission_id = str(uuid.uuid4())
        
        # Insert into SQL Database
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        # Insert contact submission
        cursor.execute("""
            INSERT INTO ContactSubmissions (SubmissionId, Subject, Email, Phone, Message, ActionTaken)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (submission_id, subject, email, phone, message, 'Pending'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'ok': True,
            'id': submission_id,
            'database': SQL_DATABASE,
            'table': 'ContactSubmissions'
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
        
        # Upload image to Azure Blob Storage using Managed Identity (if available)
        image_url = None
        if blob_service_client is None and AZURE_AVAILABLE:
            try:
                init_blob_storage()
            except Exception as e:
                app.logger.warning(f'Could not initialize blob storage: {e}')
        
        if blob_service_client:
            try:
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
                
                # Get public URL with cache-busting parameter
                image_url = blob_client.url
                timestamp = int(datetime.now(timezone.utc).timestamp())
                image_url = f"{image_url}?v={timestamp}"
                app.logger.info(f'Image uploaded to blob storage: {blob_name}')
            except Exception as e:
                app.logger.warning(f'Failed to upload to blob storage: {e}')
                app.logger.info('Continuing without cloud image storage')
                # Use a placeholder or local path
                image_url = f'/assets/images/placeholder.png'
        else:
            app.logger.info('Blob storage not available, using placeholder URL')
            image_url = f'/assets/images/placeholder.png'
        
        if not image_url:
            return jsonify({'ok': False, 'error': 'Failed to process image'}), 500
        
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
    """Get products with optional filters from Cosmos DB."""
    try:
        if database is None:
            init_cosmos()
        
        products_container = database.get_container_client(PRODUCTS_CONTAINER)
        
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
        app.logger.info(f'Fetched {len(items)} products from Cosmos DB')
        
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
        app.logger.info(f'=== UPDATE PRODUCT REQUEST: {product_id} ===')
        app.logger.info(f'Content-Type: {request.content_type}')
        
        # Check authorization - only Admin users can update products
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'ok': False, 'error': 'Unauthorized. Please login.'}), 401
        
        # TEMPORARY: Skip admin verification for testing
        # TODO: Re-enable this check in production
        app.logger.info(f'User ID: {user_id}')
        # Verify user is Admin
        # conn = get_sql_connection()
        # cursor = conn.cursor()
        # cursor.execute("SELECT access_level FROM Users WHERE user_id = ? AND active = 1", (user_id,))
        # row = cursor.fetchone()
        # cursor.close()
        # conn.close()
        
        # if not row or row[0] != 'Admin':
        #     return jsonify({'ok': False, 'error': 'Unauthorized. Admin access required.'}), 403
        
        # Check if this is FormData (with image) or JSON (without image)
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData with optional image
            data = request.form.to_dict()
            image_file = request.files.get('itemImage')
            app.logger.info(f'Received FormData request. Image file: {image_file.filename if image_file else "None"}')
        else:
            # JSON without image
            data = request.get_json(force=True) or {}
            image_file = None
            app.logger.info('Received JSON request (no image)')
        
        if database is None:
            init_cosmos()
        
        products_container = database.get_container_client(PRODUCTS_CONTAINER)
        
        # Get existing product
        existing_product = products_container.read_item(item=product_id, partition_key=product_id)
        
        # Initialize blob storage if needed
        if blob_service_client is None and AZURE_AVAILABLE:
            try:
                init_blob_storage()
            except Exception as e:
                app.logger.warning(f'Could not initialize blob storage: {e}')
        
        # Handle image upload if provided
        if image_file:
            app.logger.info(f'Processing image upload. File: {image_file.filename}, Size: {image_file.content_length} bytes')
            
            # Upload new image to Blob Storage if available
            if blob_service_client:
                try:
                    file_ext = os.path.splitext(image_file.filename)[1]
                    blob_name = f"products/{product_id}{file_ext}"
                    
                    app.logger.info(f'Uploading image to blob storage: {blob_name}')
                    blob_client = blob_service_client.get_blob_client(container='product-images', blob=blob_name)
                    blob_client.upload_blob(image_file, overwrite=True, content_settings=ContentSettings(content_type=image_file.content_type))
                    image_url = blob_client.url
                    
                    # Add cache-busting query parameter to force browser to reload the image
                    timestamp = int(datetime.now(timezone.utc).timestamp())
                    image_url = f"{image_url}?v={timestamp}"
                    
                    # Delete old image if it has a different extension
                    old_image_url = existing_product.get('imageUrl', '')
                    if old_image_url and 'blob.core.windows.net' in old_image_url:
                        try:
                            clean_url = old_image_url.split('?')[0]
                            old_ext = os.path.splitext(clean_url)[1]
                            app.logger.info(f'Old image URL: {old_image_url}')
                            app.logger.info(f'Clean URL: {clean_url}')
                            app.logger.info(f'Old extension: {old_ext}, New extension: {file_ext}')
                            # Only delete if extensions are different (same extension was already overwritten)
                            if old_ext and old_ext != file_ext:
                                parts = clean_url.split('/')
                                old_blob_name = '/'.join(parts[-2:])
                                app.logger.info(f'Attempting to delete old blob: {old_blob_name}')
                                old_blob_client = blob_service_client.get_blob_client(container='product-images', blob=old_blob_name)
                                old_blob_client.delete_blob()
                                app.logger.info(f'Deleted old image with different extension: {old_blob_name}')
                            else:
                                app.logger.info(f'Skipping delete - same extension (already overwritten)')
                        except Exception as e:
                            app.logger.warning(f'Failed to delete old image: {e}')
                    
                    existing_product['imageUrl'] = image_url
                    app.logger.info(f'[OK] Image uploaded successfully: {blob_name} -> {image_url}')
                except Exception as e:
                    app.logger.error(f'Failed to upload image to Azure Blob Storage: {e}')
                    app.logger.exception('Full error trace:')
                    # Keep the old image URL
            else:
                app.logger.warning('Blob storage client not available - skipping image upload')
        
        # Update fields if provided
        if 'price' in data:
            existing_product['price'] = float(data['price'])
        if 'categories' in data:
            # Handle both JSON array and form field (comma-separated or JSON string)
            categories = data['categories']
            if isinstance(categories, str):
                try:
                    existing_product['categories'] = json.loads(categories)
                except:
                    existing_product['categories'] = [c.strip() for c in categories.split(',') if c.strip()]
            else:
                existing_product['categories'] = categories
        if 'ageGroups' in data:
            age_groups = data['ageGroups']
            if isinstance(age_groups, str):
                try:
                    existing_product['ageGroups'] = json.loads(age_groups)
                except:
                    existing_product['ageGroups'] = [a.strip() for a in age_groups.split(',') if a.strip()]
            else:
                existing_product['ageGroups'] = age_groups
        if 'seasons' in data:
            seasons = data['seasons']
            if isinstance(seasons, str):
                try:
                    existing_product['seasons'] = json.loads(seasons)
                except:
                    existing_product['seasons'] = [s.strip() for s in seasons.split(',') if s.strip()]
            else:
                existing_product['seasons'] = seasons
        if 'occasions' in data:
            occasions = data['occasions']
            if isinstance(occasions, str):
                try:
                    existing_product['occasions'] = json.loads(occasions)
                except:
                    existing_product['occasions'] = [o.strip() for o in occasions.split(',') if o.strip()]
            else:
                existing_product['occasions'] = occasions
        
        existing_product['updatedAt'] = datetime.now(timezone.utc).isoformat()
        
        # Update the product in Cosmos DB
        products_container.replace_item(item=product_id, body=existing_product)
        app.logger.info(f'Product updated successfully in Cosmos DB: {product_id}')
        
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

