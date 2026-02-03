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
DB_PASS = "PUT_PASSWORD_HERE"  # <-- put your real password locally, DON'T commit
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
# DB: product lookup (scan time)
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
            cur.execute("SELECT name, price FROM products WHERE barcode=%s", (barcode10,))
            row = cur.fetchone()
            if not row:
                return None
            name, price = row
            return str(name), float(price)
    finally:
        conn.close()

# ==============================
# DB: deduct stock (payment time)
# ==============================
def deduct_stock_after_payment(cart):
    """
    Deduct stock only after payment success.
    cart = {barcode10: qty}
    Returns True if success, False if mismatch/insufficient.
    """
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=5,
        autocommit=False
    )
    try:
        with conn.cursor() as cur:
            # 1) Check availability for all items
            for barcode10, qty in cart.items():
                cur.execute("SELECT stock FROM products WHERE barcode=%s", (barcode10,))
                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    return False

                stock = int(row[0])
                if stock < qty:
                    conn.rollback()
                    return False

            # 2) Deduct stock for all items
            for barcode10, qty in cart.items():
                cur.execute(
                    "UPDATE products SET stock = stock - %s WHERE barcode=%s",
                    (qty, barcode10)
                )

        conn.commit()
        return True

    except Exception as e:
        print("[ERROR] deduct_stock_after_payment:", e, flush=True)
        conn.rollback()
        return False

    finally:
        conn.close()

# ==============================
# LCD PAGES
# ==============================
def show_in_store_page(lcd, total):
    lcd.lcd_clear()
    lcd.lcd_display_string("Scan item...", 1)
    lcd.lcd_display_string(f"T:${total:.2f}  #Pay"[:16], 2)

def show_online_pickup_page(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Online Pickup", 1)
    lcd.lcd_display_string("Scan QR *=Back", 2)

def show_checkout_menu(lcd, total):
    lcd.lcd_clear()
    lcd.lcd_display_string("1.ATM 2.PayWave", 1)
    lcd.lcd_display_string(f"Tot:${total:.2f} *=Back"[:16], 2)

def show_atm_prompt(lcd, pin_len=0):
    lcd.lcd_clear()
    lcd.lcd_display_string("Enter PIN:", 1)
    masked = "*" * pin_len + "_" * (4 - pin_len)
    lcd.lcd_display_string((masked + " *=Back")[:16], 2)

def show_paywave_prompt(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Tap RFID Card", 1)
    lcd.lcd_display_string("*=Back", 2)

def show_payment_ok(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Payment", 1)
    lcd.lcd_display_string("SUCCESS", 2)

def show_assistance_needed(lcd):
    """
    Stock mismatch / system mismatch message
    (better UX than 'out of stock')
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("Assistance", 1)
    lcd.lcd_display_string("Needed", 2)

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

    while True:
        if time.time() - start > timeout:
            return None

        try:
            k = shared_q.get(timeout=0.1)
        except queue.Empty:
            continue

        if k == "*":
            return None

        if isinstance(k, int) and 0 <= k <= 9:
            pin += str(k)
            show_atm_prompt(lcd, len(pin))
            if len(pin) == 4:
                return pin

def read_rfid_id(rfid, timeout=15):
    start = time.time()
    while True:
        if time.time() - start > timeout:
            return None
        card_id = rfid.read_id_no_block()
        if card_id is not None:
            return str(card_id)
        time.sleep(0.1)

# ==============================
# MAIN PROGRAM
# ==============================
def main():
    current_state = STATE_MENU_1
    last_key_time = time.time()

    cart_total = 0.0
    cart = {}  # barcode10 -> qty (important!)
    scanner_available = True

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

    # Barcode scanner init (once)
    try:
        scanner = BarcodeScanner(show_preview=True)
        print("[INFO] Camera scanner ready", flush=True)
    except Exception as e:
        scanner_available = False
        scanner = None
        print("[ERROR] Scanner init failed:", e, flush=True)

    # Startup + menu
    menu.startup_screen(lcd)
    menu.menu_page_1(lcd, scanner_available)
    last_key_time = time.time()

    while True:
        # REQ-05 inactivity timeout only on menu screen
        if time.time() - last_key_time > 30:
            if current_state == STATE_MENU_1:
                menu.menu_page_1(lcd, scanner_available)

        try:
            keyvalue = shared_keypad_queue.get(timeout=0.1)
            last_key_time = time.time()
        except queue.Empty:
            keyvalue = None

        # '*' global back (cancel)
        if keyvalue == "*":
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd, scanner_available)
            continue

        # ==============================
        # MENU PAGE 1
        # ==============================
        if current_state == STATE_MENU_1 and keyvalue is not None:

            # 1 = Online Pickup (QR ONLY)
            if keyvalue == 1:
                if not scanner_available or scanner is None:
                    menu.scanner_error(lcd)
                    menu.menu_page_1(lcd, scanner_available)
                    continue

                current_state = STATE_ONLINE_PICKUP
                show_online_pickup_page(lcd)
                continue

            # 2 = In-Store Purchase (BARCODE ONLY)
            if keyvalue == 2:
                cart_total = 0.0
                cart = {}
                current_state = STATE_IN_STORE
                show_in_store_page(lcd, cart_total)
                continue

            menu.invalid_input(lcd)
            menu.menu_page_1(lcd, scanner_available)
            continue

        # ==============================
        # ONLINE PICKUP MODE (QR ONLY)
        # ==============================
        if current_state == STATE_ONLINE_PICKUP:

            if not scanner_available or scanner is None:
                menu.scanner_error(lcd)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)
                continue

            show_online_pickup_page(lcd)

            qr_text = scanner.scan_once(timeout=2, mode="qr")

            if qr_text:
                qr_text = str(qr_text).strip()

                print("QR SCANNED:", qr_text, flush=True)

                lcd.lcd_clear()
                lcd.lcd_display_string("QR Detected!", 1)
                lcd.lcd_display_string(qr_text[:16], 2)

                buzzer.beep(0.2, 0.0, 1)
                time.sleep(2)

                # After success → return to menu (later validate QR in DB)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)

            continue

        # ==============================
        # IN-STORE MODE (AUTO SCAN)
        # ==============================
        if current_state == STATE_IN_STORE:

            # if user presses '#', go to checkout menu
            if keyvalue == "#":
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            if not scanner_available or scanner is None:
                menu.scanner_error(lcd)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)
                continue

            show_in_store_page(lcd, cart_total)

            code = scanner.scan_once(timeout=2, mode="barcode")

            if code:
                raw = str(code).strip()
                barcode10 = raw.zfill(BARCODE_LEN)

                print("BARCODE SCANNED:", barcode10, flush=True)

                product = get_product_by_barcode(barcode10)
                if product is None:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Not Found", 1)
                    lcd.lcd_display_string(barcode10[:16], 2)
                    time.sleep(1.2)
                    continue

                name, price = product

                # Update cart in memory ONLY (no DB deduction yet)
                cart[barcode10] = cart.get(barcode10, 0) + 1
                cart_total += price

                lcd.lcd_clear()
                lcd.lcd_display_string(f"{name} ${price:.2f}"[:16], 1)
                lcd.lcd_display_string(f"Total ${cart_total:.2f}"[:16], 2)

                buzzer.beep(0.2, 0.0, 1)
                time.sleep(2)

            continue

        # ==============================
        # CHECKOUT MENU
        # ==============================
        if current_state == STATE_CHECKOUT and keyvalue is not None:
            if keyvalue == 1:
                current_state = STATE_ATM_PIN
                show_atm_prompt(lcd, 0)
                continue
            elif keyvalue == 2:
                current_state = STATE_PAYWAVE
                show_paywave_prompt(lcd)
                continue
            else:
                menu.invalid_input(lcd)
                show_checkout_menu(lcd, cart_total)
                continue

        # ==============================
        # ATM PAYMENT
        # ==============================
        if current_state == STATE_ATM_PIN:
            pin = read_pin(shared_keypad_queue, lcd, timeout=20)
            if pin is None:
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            # Demo PIN
            if pin != "1234":
                show_wrong_pin(lcd)
                time.sleep(2)
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            # PIN ok → NOW deduct stock
            ok = deduct_stock_after_payment(cart)
            if not ok:
                show_assistance_needed(lcd)
                time.sleep(2)
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            show_payment_ok(lcd)
            time.sleep(2)

            # Reset cart after success
            cart_total = 0.0
            cart = {}
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd, scanner_available)
            continue

        # ==============================
        # PAYWAVE (RFID)
        # ==============================
        if current_state == STATE_PAYWAVE:
            show_paywave_prompt(lcd)
            card_id = read_rfid_id(rfid, timeout=15)

            if card_id is None:
                show_assistance_needed(lcd)
                time.sleep(2)
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            print("RFID CARD:", card_id, flush=True)

            # Card tapped → NOW deduct stock
            ok = deduct_stock_after_payment(cart)
            if not ok:
                show_assistance_needed(lcd)
                time.sleep(2)
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            show_payment_ok(lcd)
            time.sleep(2)

            # Reset cart after success
            cart_total = 0.0
            cart = {}
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd, scanner_available)
            continue


if __name__ == "__main__":
    main()
