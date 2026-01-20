import pymysql

# ---------- DATABASE CONNECTION ----------
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="spmart_user",
        password="spmart123",
        database="spmart"
    )

# ---------- AUTO-GENERATE PRODUCT ID ----------
def generate_product_id(cur):
    cur.execute("SELECT MAX(product_id) FROM products")
    row = cur.fetchone()

    if row is None or row[0] is None:
        return 1

    return int(row[0]) + 1


# ---------- VIEW INVENTORY ----------
def show_inventory():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT product_id, name, price, inventory FROM products")

    print("\n=== INVENTORY ===")
    print("ID | Name | Price | Stock")
    print("-" * 35)

    for row in cur.fetchall():
        print(row)

    conn.close()

# ---------- ADD NEW PRODUCT ----------
def add_product():
    name = input("Product name: ")
    price = float(input("Price: "))
    inventory = int(input("Inventory quantity: "))

    conn = get_connection()
    cur = conn.cursor()

    product_id = generate_product_id(cur)

    sql = """
    INSERT INTO products (product_id, name, price, inventory)
    VALUES (%s, %s, %s, %s)
    """
    cur.execute(sql, (product_id, name, price, inventory))

    conn.commit()
    conn.close()

    print(f"Product added successfully (ID: {product_id})")

# ---------- UPDATE INVENTORY ----------
def update_inventory():
    product_id = int(input("Enter product ID: "))
    new_inventory = int(input("Enter new inventory value: "))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE products SET inventory = %s WHERE product_id = %s",
        (new_inventory, product_id)
    )

    conn.commit()
    conn.close()

    print("Inventory updated successfully")

# ---------- ADJUST INVENTORY ----------
def adjust_inventory():
    product_id = int(input("Enter product ID: "))
    change = int(input("Enter change (+ add, - reduce): "))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE products SET inventory = inventory + %s WHERE product_id = %s",
        (change, product_id)
    )

    conn.commit()
    conn.close()

    print("Inventory adjusted successfully")

# ---------- MAIN MENU ----------
def main():
    while True:
        print("\n===== INVENTORY MANAGEMENT =====")
        print("1. View inventory")
        print("2. Add new product")
        print("3. Update inventory (set value)")
        print("4. Adjust inventory (+ / -)")
        print("5. Exit")

        choice = input("Choose option: ")

        if choice == "1":
            show_inventory()
        elif choice == "2":
            add_product()
        elif choice == "3":
            update_inventory()
        elif choice == "4":
            adjust_inventory()
        elif choice == "5":
            print("Goodbye")
            break
        else:
            print("Invalid choice")

# ---------- RUN ----------
if __name__ == "__main__":
    main()