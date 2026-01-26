from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "super_secret_company_key"

UPLOAD_FOLDER = "static/images/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3006,
        user="kai_user",
        password="mypassword123",
        database="supermarket",
        auth_plugin="mysql_native_password"
    )

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- PROTECTED HOME ----------------
@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", products=products)

# ---------------- ADD PRODUCT ----------------
@app.route("/add-product", methods=["POST"])
def add_product():
    name = request.form["name"]
    price = request.form["price"]
    stock = request.form["stock"]
    image = request.files["image"]

    filename = image.filename
    image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, stock, image) VALUES (%s,%s,%s,%s)",
        (name, price, stock, filename)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("home"))

# ---------------- EDIT PRICE & STOCK ----------------
@app.route("/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if request.method == "POST":
        price = request.form["price"]
        stock = request.form["stock"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET price=%s, stock=%s WHERE product_id=%s",
            (price, stock, product_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_id=%s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("edit.html", product=product)

if __name__ == "__main__":
    app.run(debug=True)
