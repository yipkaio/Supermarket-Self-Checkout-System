import time
from threading import Thread
import queue
import pymysql

from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_adc as adc
from hal import hal_buzzer as buzzer
from hal import hal_keypad as keypad
from hal import hal_moisture_sensor as moisture_sensor
from hal import hal_input_switch as input_switch
from hal import hal_ir_sensor as ir_sensor
from hal import hal_rfid_reader as rfid_reader
from hal import hal_servo as servo
from hal import hal_temp_humidity_sensor as temp_humid_sensor
from hal import hal_usonic as usonic
from hal import hal_dc_motor as dc_motor
from hal import hal_accelerometer as accel

import menu
from barcode_scanner import BarcodeScanner

# ==============================
# DATABASE CONFIG (Railway MySQL)
# ==============================
DB_HOST = "metro.proxy.rlwy.net"
DB_PORT = 48897
DB_USER = "root"
DB_PASS = "YOdvGwlAhmzIWuoFjPnrYddwuGdqfFwm"   # ❗ DO NOT COMMIT
DB_NAME = "railway"
BARCODE_LEN = 10

# ==============================
# SYSTEM STATES
# ==============================
STATE_MENU_1 = 1
STATE_ONLINE_PICKUP = 2
STATE_IN_STORE = 3
STATE_CHECKOUT = 4
STATE_ATM_PIN = 5
STATE_PAYWAVE = 6

shared_keypad_queue = queue.Queue()

# ==============================
# KEYPAD CALLBACK
# ==============================
def key_pressed(key):
    print("KEY PRESSED:", key, flush=True)
    shared_keypad_queue.put(key)

# ==============================
# DB: PRODUCT LOOKUP (IN-STORE)
# ==============================
def get_product_by_barcode(barcode10):
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=5
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, price FROM products WHERE barcode=%s",
                (barcode10,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return str(row[0]), float(row[1])
    finally:
        conn.close()

# ==============================
# DB: ONLINE PICKUP QR LOOKUP
# ==============================
def get_pickup_id_by_qr(qr_code):
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=5
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pickup_id FROM pickup_orders WHERE qr_code=%s",
                (qr_code,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return row[0]
    finally:
        conn.close()

# ==============================
# DB: DEDUCT STOCK AFTER PAYMENT
# ==============================
def deduct_stock_after_payment(cart):
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=False
    )
    try:
        with conn.cursor() as cur:
            for barcode10, qty in cart.items():
                cur.execute(
                    "SELECT stock FROM products WHERE barcode=%s",
                    (barcode10,)
                )
                row = cur.fetchone()
                if row is None or int(row[0]) < qty:
                    conn.rollback()
                    return False

            for barcode10, qty in cart.items():
                cur.execute(
                    "UPDATE products SET stock = stock - %s WHERE barcode=%s",
                    (qty, barcode10)
                )

        conn.commit()
        return True
    except Exception as e:
        print("[ERROR]", e, flush=True)
        conn.rollback()
        return False
    finally:
        conn.close()

# ==============================
# LCD PAGES
# ==============================
def show_online_pickup_page(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Online Pickup", 1)
    lcd.lcd_display_string("Scan QR *=Back", 2)

def show_in_store_page(lcd, total):
    lcd.lcd_clear()
    lcd.lcd_display_string("Scan item...", 1)
    lcd.lcd_display_string(f"T:${total:.2f} #Pay"[:16], 2)

def show_checkout_menu(lcd, total):
    lcd.lcd_clear()
    lcd.lcd_display_string("1.ATM 2.PayWave", 1)
    lcd.lcd_display_string(f"Tot:${total:.2f} *=Back"[:16], 2)

def show_atm_prompt(lcd, pin_len):
    lcd.lcd_clear()
    lcd.lcd_display_string("Enter PIN:", 1)
    lcd.lcd_display_string("*" * pin_len + "_" * (4 - pin_len), 2)

def show_paywave_prompt(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Tap RFID Card", 1)
    lcd.lcd_display_string("*=Back", 2)

def show_payment_ok(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Payment", 1)
    lcd.lcd_display_string("SUCCESS", 2)

def show_wrong_pin(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Wrong PIN", 1)
    lcd.lcd_display_string("Try Again", 2)

# ==============================
# PAYMENT HELPERS
# ==============================
def read_pin(shared_q, lcd, timeout=20):
    pin = ""
    start = time.time()
    show_atm_prompt(lcd, len(pin))

    while time.time() - start < timeout:
        try:
            k = shared_q.get(timeout=0.1)
        except queue.Empty:
            continue

        if k == "*":
            return None

        if isinstance(k, int):
            pin += str(k)
            show_atm_prompt(lcd, len(pin))
            if len(pin) == 4:
                return pin
    return None

def read_rfid_id(rfid, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        card = rfid.read_id_no_block()
        if card:
            return str(card)
        time.sleep(0.1)
    return None

# ==============================
# MAIN PROGRAM
# ==============================
def main():
    current_state = STATE_MENU_1
    cart_total = 0.0
    cart = {}

    # HAL init
    led.init()
    adc.init()
    buzzer.init()
    moisture_sensor.init()
    input_switch.init()
    ir_sensor.init()
    rfid = rfid_reader.init()
    servo.init()
    temp_humid_sensor.init()
    usonic.init()
    dc_motor.init()
    accel.init()

    keypad.init(key_pressed)
    Thread(target=keypad.get_key, daemon=True).start()

    lcd = LCD.lcd()

    # Camera init
    scanner = BarcodeScanner(show_preview=True)

    menu.startup_screen(lcd)
    menu.menu_page_1(lcd, True)

    while True:
        try:
            keyvalue = shared_keypad_queue.get(timeout=0.1)
        except queue.Empty:
            keyvalue = None

        if keyvalue == "*":
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd, True)
            continue

        # ==============================
        # MENU
        # ==============================
        if current_state == STATE_MENU_1 and keyvalue is not None:
            if keyvalue == 1:
                current_state = STATE_ONLINE_PICKUP
                show_online_pickup_page(lcd)
                continue

            if keyvalue == 2:
                cart_total = 0.0
                cart = {}
                current_state = STATE_IN_STORE
                show_in_store_page(lcd, cart_total)
                continue

            menu.invalid_input(lcd)
            menu.menu_page_1(lcd, True)

        # ==============================
        # ONLINE PICKUP (QR ONLY)
        # ==============================
        if current_state == STATE_ONLINE_PICKUP:
            qr = scanner.scan_once(timeout=2, mode="qr")
            if qr:
                pickup_id = get_pickup_id_by_qr(qr)
                if pickup_id:
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Order {pickup_id}"[:16], 1)
                    lcd.lcd_display_string("Collected", 2)
                    buzzer.beep(0.2, 0, 1)
                    time.sleep(3)
                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Invalid QR", 1)
                    lcd.lcd_display_string("Call Staff", 2)
                    time.sleep(2)

                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, True)

        # ==============================
        # IN-STORE BARCODE SCANNING
        # ==============================
        if current_state == STATE_IN_STORE:
            if keyvalue == "#":
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            code = scanner.scan_once(timeout=2, mode="barcode")
            if code:
                barcode10 = code.zfill(BARCODE_LEN)
                product = get_product_by_barcode(barcode10)

                if not product:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Not Found", 1)
                    lcd.lcd_display_string(barcode10[:16], 2)
                    time.sleep(1.5)
                    continue

                name, price = product
                cart[barcode10] = cart.get(barcode10, 0) + 1
                cart_total += price

                lcd.lcd_clear()
                lcd.lcd_display_string(f"{name} ${price:.2f}"[:16], 1)
                lcd.lcd_display_string(f"Total ${cart_total:.2f}"[:16], 2)
                buzzer.beep(0.2, 0, 1)
                time.sleep(2)

        # ==============================
        # CHECKOUT
        # ==============================
        if current_state == STATE_CHECKOUT and keyvalue is not None:
            if keyvalue == 1:
                current_state = STATE_ATM_PIN
                continue
            if keyvalue == 2:
                current_state = STATE_PAYWAVE
                show_paywave_prompt(lcd)

        if current_state == STATE_ATM_PIN:
            pin = read_pin(shared_keypad_queue, lcd)
            if pin != "1234":
                show_wrong_pin(lcd)
                time.sleep(2)
                current_state = STATE_CHECKOUT
                continue

            deduct_stock_after_payment(cart)
            show_payment_ok(lcd)
            time.sleep(2)
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd, True)

        if current_state == STATE_PAYWAVE:
            card = read_rfid_id(rfid)
            if card:
                deduct_stock_after_payment(cart)
                show_payment_ok(lcd)
                time.sleep(2)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, True)

if __name__ == "__main__":
    main()
