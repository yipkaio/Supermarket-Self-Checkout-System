from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============ CONFIGURATION ============
UPLOAD_FOLDER = 'static/images/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============ DATABASE CONFIG ============
DB_CONFIG = {
    'host': 'metro.proxy.rlwy.net',
    'port': 48897,  # Change to 3006 if needed
    'user': 'root',  # Change to your MySQL username
    'password': 'YOdvGwlAhmzIWuoFjPnrYddwuGdqfFwm',  # Change to your MySQL password
    'database': 'railway'
}

def get_db_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
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
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
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
        print(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert Decimal to float for JSON serialization
        for product in products:
            product['price'] = float(product['price'])
        
        return jsonify(products), 200
        
    except Exception as e:
        print(f"Get products error: {e}")
        return jsonify({
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    """Create new product"""
    try:
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '0')
        stock = request.form.get('stock', '0')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Product name is required'
            }), 400
        
        # Handle image upload
        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                # Create unique filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                original_filename = secure_filename(file.filename)
                filename = f"{timestamp}_{original_filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                print(f"Image saved: {filepath}")
        
        # Insert into database
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        query = """
            INSERT INTO products (name, price, stock, image) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (name, float(price), int(stock), filename))
        conn.commit()
        
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Product created successfully',
            'product_id': new_id
        }), 201
        
    except Exception as e:
        print(f"Create product error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/products/', methods=['PUT'])
def update_product(product_id):
    """Update product"""
    try:
        data = request.get_json()
        price = data.get('price')
        stock = data.get('stock')
        
        if price is None or stock is None:
            return jsonify({
                'success': False,
                'error': 'Price and stock are required'
            }), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor()
        query = """
            UPDATE products 
            SET price = %s, stock = %s 
            WHERE product_id = %s
        """
        cursor.execute(query, (float(price), int(stock), product_id))
        conn.commit()
        
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected == 0:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Product updated successfully'
        }), 200
        
    except Exception as e:
        print(f"Update product error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/products/', methods=['DELETE'])
def delete_product(product_id):
    """Delete product"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        # Get image filename before deleting
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT image FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            cursor.close()
            conn.close()
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
                os.remove(image_path)
                print(f"Deleted image: {image_path}")
        
        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Delete product error: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/static/images/uploads/')
def serve_image(filename):
    """Serve uploaded images"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============ RUN SERVER ============
if __name__ == '__main__':
    print("=" * 50)
    print("Flask Server Starting...")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print("API Endpoints:")
    print("  - GET  /api/health")
    print("  - POST /api/login")
    print("  - GET  /api/products")
    print("  - POST /api/products")
    print("  - PUT  /api/products/")
    print("  - DELETE /api/products/")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
