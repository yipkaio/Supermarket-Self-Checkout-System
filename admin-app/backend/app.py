from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# CORS Configuration
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "supports_credentials": True
    }
})

# Configuration
UPLOAD_FOLDER = 'static/images/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Configuration - UPDATE THIS!
DB_CONFIG = {
    'host': 'metro.proxy.rlwy.net',
    'port': 48897,  
    'user': 'root',  
    'password': 'YOdvGwlAhmzIWuoFjPnrYddwuGdqfFwm', 
    'database': 'railway'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"❌ Database error: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response, 200

@app.route('/api/health', methods=['GET'])
def health_check():
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'status': 'success', 'message': 'API running'}), 200
    return jsonify({'status': 'error', 'message': 'DB connection failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return jsonify({
                'success': True,
                'user': {'user_id': user['user_id'], 'username': user['username']}
            }), 200
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for product in products:
            product['price'] = float(product['price'])
        
        return jsonify(products), 200
    except Exception as e:
        print(f"❌ Get products error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def create_product():
    try:
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '0')
        stock = request.form.get('stock', '0')
        
        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, price, stock, image) VALUES (%s, %s, %s, %s)",
            (name, float(price), int(stock), filename)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        print(f"✅ Created product: {name} (ID: {new_id})")
        return jsonify({'success': True, 'product_id': new_id}), 201
    except Exception as e:
        print(f"❌ Create error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT', 'OPTIONS'])
def update_product(product_id):
    try:
        print(f"📝 PUT request for product ID: {product_id}")
        
        data = request.get_json()
        price = float(data.get('price'))
        stock = int(data.get('stock'))
        
        print(f"   Updating to: price=${price}, stock={stock}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET price = %s, stock = %s WHERE product_id = %s",
            (price, stock, product_id)
        )
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected == 0:
            print(f"⚠️ Product {product_id} not found")
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        print(f"✅ Updated product {product_id}")
        return jsonify({'success': True, 'message': 'Product updated'}), 200
    except Exception as e:
        print(f"❌ Update error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE', 'OPTIONS'])
def delete_product(product_id):
    try:
        print(f"🗑️ DELETE request for product ID: {product_id}")
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT image FROM products WHERE product_id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            cursor.close()
            conn.close()
            print(f"⚠️ Product {product_id} not found")
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        if product['image']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        print(f"✅ Deleted product {product_id}")
        return jsonify({'success': True, 'message': 'Product deleted'}), 200
    except Exception as e:
        print(f"❌ Delete error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/static/images/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Debug: List routes
def list_routes():
    print("\n" + "=" * 60)
    print("📋 REGISTERED ROUTES:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"   {methods:10s} {rule.rule}")
    print("=" * 60 + "\n")

list_routes()

if __name__ == '__main__':
    print("🚀 Starting Flask on http://localhost:5000")
    print(f"📁 Uploads: {os.path.abspath(UPLOAD_FOLDER)}")
    print("🌐 CORS enabled for http://localhost:5173\n")
    app.run(host='0.0.0.0', port=5000, debug=True)