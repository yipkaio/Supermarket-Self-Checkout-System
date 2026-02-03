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
    print("-" * 40)

    for product_id, name, price, inventory in cur.fetchall():
        print(f"{product_id} | {name} | ${float(price):.2f} | {inventory}")

    conn.close()


# ---------- ADD NEW PRODUCT ----------
def add_product():
    name = input("Product name: ")
    price = input("Price: ")
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


# ---------- UPDATE INVENTORY (SET VALUE) ----------
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

    if cur.rowcount == 0:
        print("No such product found.")
    else:
        print("Inventory updated successfully.")

    conn.close()


# ---------- ADJUST INVENTORY (+ / -) ----------
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

    if cur.rowcount == 0:
        print("No such product found.")
    else:
        print("Inventory adjusted successfully.")

    conn.close()


# ---------- DELETE PRODUCT ----------
def delete_product():
    product_id = int(input("Enter product ID to delete: "))

    confirm = input(f"Are you sure you want to delete product {product_id}? (y/n): ").lower()
    if confirm != "y":
        print("Delete cancelled.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
    conn.commit()

    if cur.rowcount == 0:
        print("No such product found. Nothing deleted.")
    else:
        print("Product deleted successfully.")

    conn.close()


# ---------- MAIN MENU ----------
def main():
    while True:
        print("\n===== INVENTORY MANAGEMENT =====")
        print("1. View inventory")
        print("2. Add new product")
        print("3. Update inventory (set value)")
        print("4. Adjust inventory (+ / -)")
        print("5. Delete product")
        print("6. Exit")

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
            delete_product()
        elif choice == "6":
            print("Goodbye")
            break
        else:
            print("Invalid choice")


# ---------- RUN ----------
if __name__ == "__main__":
    main()