from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
import uuid
import qrcode
from flask import send_from_directory


app = Flask(__name__)
CORS(app)
@app.route('/barcodes/<filename>')
def serve_qr(filename):
    return send_from_directory('qrcodes', filename)

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return mysql.connector.connect(
        host="metro.proxy.rlwy.net",    
        port=48897,
        user="root",
        password="YOdvGwlAhmzIWuoFjPnrYddwuGdqfFwm",
        database="railway"
    )

# ---------------- IMAGE SERVER ----------------
@app.route("/images/<filename>")
def serve_image(filename):
    return send_from_directory(os.path.join(os.getcwd(), "upload"), filename)

# ---------------- PRODUCTS ----------------
@app.route("/products", methods=["GET"])
def get_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(products)

# ---------------- ADD PRODUCT ----------------
@app.route("/add-product", methods=["POST"])
def add_product():
    data = request.json
    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)",
        (name, price, stock)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Product added successfully"})

# ---------------- REGISTER / LOGIN ----------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT user_id, password FROM users WHERE username = %s",
        (username,)
    )
    user = cursor.fetchone()

    if user:
        if user["password"] == password:
            cursor.close()
            conn.close()
            return jsonify({
                "message": "Welcome back",
                "user_id": user["user_id"]
            }), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({"message": "Wrong password"}), 401

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (username, password)
    )
    user_id = cursor.lastrowid

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": "Welcome",
        "user_id": user_id
    }), 201

# ---------------- CHECKOUT ----------------
@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.json
    user_id = data.get("user_id")
    items = data.get("items")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    total = 0

    for item in items:
        cursor.execute(
            "SELECT price, stock FROM products WHERE product_id = %s",
            (item["product_id"],)
        )
        product = cursor.fetchone()

        if not product:
            return jsonify({"error": "Product not found"}), 400

        if product["stock"] < item["quantity"]:
            return jsonify({"error": "Insufficient stock"}), 400

        total += product["price"] * item["quantity"]

    cursor.execute(
        "INSERT INTO transactions (total, user_id) VALUES (%s, %s)",
        (total, user_id)
    )
    transaction_id = cursor.lastrowid

    for item in items:
        cursor.execute(
            "SELECT price FROM products WHERE product_id = %s",
            (item["product_id"],)
        )
        price = cursor.fetchone()["price"]

        cursor.execute(
            """
            INSERT INTO transaction_items
            (transaction_id, product_id, quantity, price_at_purchase)
            VALUES (%s, %s, %s, %s)
            """,
            (transaction_id, item["product_id"], item["quantity"], price)
        )

        cursor.execute(
            "UPDATE products SET stock = stock - %s WHERE product_id = %s",
            (item["quantity"], item["product_id"])
        )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": "Checkout successful",
        "transaction_id": transaction_id,
        "total": total
    })

@app.route("/create-pickup", methods=["POST"])
def create_pickup():
    try:
        print("\n=== CREATE PICKUP START ===")

        data = request.json
        username = data.get("username")
        items = data.get("items")

        print("DATA:", username, items)

        if not username or not items:
            return jsonify({"error": "Missing data"}), 400

        # generate QR value
        qr_value = str(uuid.uuid4())[:12]
        print("QR VALUE:", qr_value)

        # save QR image
        folder = "qrcodes"
        os.makedirs(folder, exist_ok=True)

        filename = f"{qr_value}.png"
        filepath = os.path.join(folder, filename)

        img = qrcode.make(qr_value)
        img.save(filepath)

        print("QR IMAGE SAVED:", filepath)

        # save to MySQL
        conn = get_db_connection()
        cursor = conn.cursor()

        for item in items:
            cursor.execute("""
                INSERT INTO pickup
                (username, product_id, product_name, quantity, qr_code)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                username,
                item["product_id"],
                item["product_name"],
                item["quantity"],
                qr_value
            ))

        conn.commit()
        cursor.close()
        conn.close()

        print("DB INSERT DONE")

        return jsonify({
            "qr_code": qr_value,
            "qr_image": f"/barcodes/{filename}"
        }), 200


    except Exception as e:
        print("❌ ERROR:", e)
        return jsonify({"error": str(e)}), 500



# ---------------- TEMP VERIFY BARCODE ----------------
@app.route("/temp-verify/<barcode>", methods=["GET"])
def temp_verify(barcode):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT product_id, product_name, quantity, barcode, username
        FROM pickup
        WHERE barcode = %s
    """, (barcode,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return jsonify({
            "valid": False,
            "message": "Barcode not found"
        }), 404

    return jsonify({
        "valid": True,
        "barcode": barcode,
        "username": rows[0]["username"],
        "items": rows
    }), 200

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
