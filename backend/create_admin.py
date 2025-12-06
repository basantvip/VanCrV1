"""Create or update an admin user for testing."""
import pyodbc
import bcrypt
import uuid

SQL_SERVER = 'vancrsql2025.database.windows.net'
SQL_DATABASE = 'VanCr'

# Try to find ODBC driver
drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]
if not drivers:
    print("No SQL Server ODBC driver found!")
    exit(1)

driver = drivers[0]
print(f"Using ODBC driver: {driver}")

# Using SQL authentication (replace with actual credentials if needed)
# Or we can use Azure AD auth if configured
try:
    from azure.identity import AzureCliCredential
    credential = AzureCliCredential()
    
    # Get token for SQL
    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"Authentication=ActiveDirectoryInteractive;"
    )
    
    attrs_before = {1256: token_struct}  # SQL_COPT_SS_ACCESS_TOKEN
    conn = pyodbc.connect(connection_string, attrs_before=attrs_before)
    print("Connected with Azure AD")
except:
    print("Azure AD auth failed, trying without token...")
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
    )
    conn = pyodbc.connect(connection_string)

cursor = conn.cursor()

# Check if admin user exists
admin_email = "admin@vancr.local"
cursor.execute("SELECT user_id, access_level FROM Users WHERE email = ?", (admin_email,))
row = cursor.fetchone()

if row:
    user_id = row[0]
    print(f"Found existing user: {admin_email}")
    print(f"Current access level: {row[1]}")
    
    # Update to Admin if not already
    if row[1] != 'Admin':
        cursor.execute("UPDATE Users SET access_level = 'Admin', active = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        print("✓ Updated user to Admin")
    else:
        print("User is already Admin")
else:
    # Create new admin user
    user_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    cursor.execute("""
        INSERT INTO Users (user_id, email, first_name, last_name, phone, active, access_level)
        VALUES (?, ?, ?, ?, ?, 1, 'Admin')
    """, (user_id, admin_email, "Admin", "User", None))
    
    cursor.execute("""
        INSERT INTO User_Credentials (user_id, password_hash)
        VALUES (?, ?)
    """, (user_id, password_hash))
    
    conn.commit()
    print(f"✓ Created new Admin user: {admin_email}")
    print(f"  Password: admin123")

print(f"\nUser ID: {user_id}")
print(f"Email: {admin_email}")
print("\nYou can now login with these credentials!")

cursor.close()
conn.close()
