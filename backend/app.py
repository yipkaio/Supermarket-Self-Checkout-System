from flask import Flask, jsonify, request,render_template
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3006,
        user="kai_user",
        password="mypassword123",
        database="supermarket",
        auth_plugin="mysql_native_password"
    )



@app.route("/")
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", products=products)

def get_products():
    conn = get_db_connection

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(products)


@app.route("/add-product", methods=["POST"])
def add_product():
    data = request.json

    name = data["name"]
    price = data["price"]
    stock = data["stock"]

    conn = get_db_connection

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)",
        (name, price, stock)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Product added successfully"})


@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.json
    items = data["items"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    total = 0

    # Check stock and calculate total amount spend 
    for item in items:
        cursor.execute(
            "SELECT price, stock FROM products WHERE product_id = %s",
            (item["product_id"],)
        )
        product = cursor.fetchone()

        if product is None:
            return jsonify({"error": "Product not found"}), 400

        if product["stock"] < item["quantity"]:
            return jsonify({"error": "Insufficient stock"}), 400

        total += product["price"] * item["quantity"]

    # create transaction
    cursor.execute(
        "INSERT INTO transactions (total) VALUES (%s)",
        (total,)
    )
    transaction_id = cursor.lastrowid

    # save item and update stock 
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



if __name__ == "__main__":
    app.run(debug=True)


