from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import time

app = Flask(__name__)

# ============ CORS CONFIGURATION ============
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "supports_credentials": True
    }
})

# ============ APP CONFIGURATION ============
UPLOAD_FOLDER = 'static/images/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============ DATABASE CONFIGURATION ============
# ⚠️ UPDATE THESE VALUES WITH YOUR MYSQL CREDENTIALS
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# ============ HELPER FUNCTIONS ============

def get_db_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"❌ Database connection error: {e}")
        return None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_barcode():
    """Generate a unique 10-digit barcode"""
    max_attempts = 100
    for _ in range(max_attempts):
        # Format: 2 (retail) + 2-digit category + 7 random digits
        category = str(random.randint(0, 99)).zfill(2)
        unique_part = str(random.randint(0, 9999999)).zfill(7)
        barcode_num = '2' + category + unique_part
        
        # Check if barcode already exists
        if not check_barcode_exists(barcode_num):
            return barcode_num
    
    # Fallback: use timestamp-based barcode
    timestamp = str(int(time.time()))[-9:]
    return '2' + timestamp

def check_barcode_exists(barcode_num):
    """Check if barcode already exists in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products WHERE barcode = %s", (barcode_num,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count > 0
    except Exception as e:
        print(f"❌ Barcode check error: {e}")
        return False

# ============ PREFLIGHT REQUEST HANDLER ============
@app.before_request
def handle_preflight():
    """Handle CORS preflight requests"""
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response, 200

# ============ API ROUTES ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            return jsonify({
                'status': 'success',
                'message': 'API and Database connected!',
                'timestamp': datetime.now().isoformat()
            }), 200
        return jsonify({
            'status': 'error',
            'message': 'Database connection failed'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'user_id': user['user_id'],
                    'username': user['username']
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid username or password'
            }), 401
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert Decimal to float for JSON serialization
        for product in products:
            if product['price']:
                product['price'] = float(product['price'])
        
        print(f"✅ Retrieved {len(products)} products")
        return jsonify(products), 200
        
    except Exception as e:
        print(f"❌ Get products error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    """Create new product with barcode"""
    try:
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '0')
        stock = request.form.get('stock', '0')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Product name is required'
            }), 400
        
        # Generate unique barcode
        barcode_number = generate_unique_barcode()
        print(f"📊 Generated barcode: {barcode_number} for {name}")
        
        # Handle image upload
        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                print(f"✅ Image saved: {filename}")
        
        # Insert into database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        query = """
            INSERT INTO products (barcode, name, price, stock, image) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (barcode_number, name, float(price), int(stock), filename))
        conn.commit()
        
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        print(f"✅ Product created: {name} (ID: {new_id}, Barcode: {barcode_number})")
        
        return jsonify({
            'success': True,
            'message': 'Product created successfully',
            'product_id': new_id,
            'barcode': barcode_number
        }), 201
        
    except Exception as e:
        print(f"❌ Create product error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update product price and stock"""
    try:
        print(f"📝 PUT request received for product ID: {product_id}")
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        price = data.get('price')
        stock = data.get('stock')
        
        print(f"   Data received: price={price}, stock={stock}")
        
        if price is None or stock is None:
            return jsonify({
                'success': False,
                'error': 'Price and stock are required'
            }), 400
        
        # Convert to proper types
        try:
            price = float(price)
            stock = int(stock)
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid data type: {str(e)}'
            }), 400
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        query = "UPDATE products SET price = %s, stock = %s WHERE product_id = %s"
        cursor.execute(query, (price, stock, product_id))
        conn.commit()
        
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected == 0:
            print(f"⚠️ Product ID {product_id} not found in database")
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        print(f"✅ Successfully updated product ID {product_id}: price=${price}, stock={stock}")
        
        return jsonify({
            'success': True,
            'message': 'Product updated successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Update product error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product"""
    try:
        print(f"🗑️ DELETE request received for product ID: {product_id}")
        
        # Connect to database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get product info before deleting (to delete image)
        cursor.execute("SELECT image FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            cursor.close()
            conn.close()
            print(f"⚠️ Product ID {product_id} not found in database")
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        # Delete from database
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Delete image file if exists
        if product['image']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'])
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    print(f"🗑️ Deleted image file: {image_path}")
                except Exception as img_error:
                    print(f"⚠️ Could not delete image: {img_error}")
        
        print(f"✅ Successfully deleted product ID {product_id}")
        
        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Delete product error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/barcode/<barcode_number>', methods=['GET'])
def get_product_by_barcode(barcode_number):
    """Get product by barcode - for scanner"""
    try:
        print(f"🔍 Barcode lookup: {barcode_number}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE barcode = %s", (barcode_number,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not product:
            print(f"⚠️ Barcode {barcode_number} not found")
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        # Convert Decimal to float
        if product['price']:
            product['price'] = float(product['price'])
        
        print(f"✅ Found product: {product['name']}")
        return jsonify({
            'success': True,
            'product': product
        }), 200
        
    except Exception as e:
        print(f"❌ Barcode lookup error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/static/images/uploads/<filename>')
def serve_image(filename):
    """Serve uploaded images"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============ DEBUG FUNCTION ============

def list_routes():
    """List all registered routes"""
    print("\n" + "=" * 70)
    print("📋 REGISTERED API ROUTES:")
    print("=" * 70)
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            routes.append((methods, rule.rule))
    
    # Sort by endpoint
    routes.sort(key=lambda x: x[1])
    
    for methods, rule in routes:
        print(f"   {methods:15s} {rule}")
    print("=" * 70 + "\n")

# ============ RUN APPLICATION ============

if __name__ == '__main__':
    list_routes()
    
    print("🚀 Flask Server Starting...")
    print(f"📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"🌐 CORS enabled for: http://localhost:5173")
    print(f"🔗 API running on: http://localhost:5000")
    print(f"📊 Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("\nPress CTRL+C to quit\n")
    
    # Bind to 0.0.0.0 to allow Docker access
    app.run(host='0.0.0.0', port=5000, debug=True)