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
from hal import hal_usonic as usonic
from hal import hal_dc_motor as dc_motor
from hal import hal_accelerometer as accel

import menu
from barcode_scanner import BarcodeScanner

# ==============================
# DATABASE CONFIG
# ==============================
DB_HOST = "metro.proxy.rlwy.net"
DB_PORT = 48897
DB_USER = "root"
DB_PASS = "YOdvGwlAhmzIWuoFjPnrYddwuGdqfFwm"
DB_NAME = "railway"
BARCODE_LEN = 10

# ==============================
# PAYWAVE RFID (HARDCODED DEMO)
# ==============================
RFID_NO_BALANCE = "506982677314"     # 0 balance -> payment failed
RFID_WITH_BALANCE = "26432748313"    # has balance -> payment success

CARD_BALANCES = {
    RFID_NO_BALANCE: 0.00,
    RFID_WITH_BALANCE: 999.00
}

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
# LED / POWER HELPERS
# ==============================
def blink_error_led():
    led.set_output(1, 1)
    time.sleep(0.2)
    led.set_output(1, 0)

def show_shutdown(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Shutting down", 1)
    lcd.lcd_display_string("Switch ON to use", 2)

def wait_for_switch_on(lcd):
    while input_switch.read_slide_switch() == 0:
        show_shutdown(lcd)
        time.sleep(0.2)
    menu.startup_screen(lcd)

# ==============================
# KEYPAD CALLBACK
# ==============================
def key_pressed(key):
    shared_keypad_queue.put(key)

# ==============================
# DB CONNECT
# ==============================
def db_connect(autocommit=True, timeout=5):
    try:
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            connect_timeout=timeout,
            read_timeout=timeout,
            write_timeout=timeout,
            autocommit=autocommit
        )
    except pymysql.MySQLError as e:
        print("[DB ERROR]", e, flush=True)
        return None

# ==============================
# DB FUNCTIONS
# ==============================
def get_product_by_barcode(barcode10):
    conn = db_connect(autocommit=True)
    if conn is None:
        return None
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

def claim_pickup_by_qr(qr_code):
    """
    pending -> collected atomically
    Returns: ("OK", pickup_id), ("ALREADY", None), ("INVALID", None), ("DB_OFFLINE", None)
    """
    conn = db_connect(autocommit=False)
    if conn is None:
        return ("DB_OFFLINE", None)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pickup_orders
                SET status='collected'
                WHERE qr_code=%s AND status='pending'
                """,
                (qr_code,)
            )

            if cur.rowcount == 1:
                cur.execute(
                    "SELECT pickup_id FROM pickup_orders WHERE qr_code=%s",
                    (qr_code,)
                )
                row = cur.fetchone()
                conn.commit()
                return ("OK", row[0] if row else None)

            cur.execute(
                "SELECT status FROM pickup_orders WHERE qr_code=%s",
                (qr_code,)
            )
            row = cur.fetchone()
            conn.rollback()

            if not row:
                return ("INVALID", None)

            return ("ALREADY", None)

    except Exception as e:
        print("[ERROR]", e, flush=True)
        conn.rollback()
        return ("DB_OFFLINE", None)
    finally:
        conn.close()

def deduct_stock_after_payment(cart):
    conn = db_connect(autocommit=False, timeout=5)
    if conn is None:
        return False

    try:
        with conn.cursor() as cur:
            # Check stock
            for barcode10, qty in cart.items():
                cur.execute("SELECT stock FROM products WHERE barcode=%s", (barcode10,))
                row = cur.fetchone()
                if row is None or int(row[0]) < qty:
                    conn.rollback()
                    return False

            # Deduct stock
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
    if total <= 0:
        lcd.lcd_display_string(f"T:${total:.2f} #Back"[:16], 2)
    else:
        lcd.lcd_display_string(f"T:${total:.2f} #Pay"[:16], 2)

def show_checkout_menu(lcd, total):
    lcd.lcd_clear()
    lcd.lcd_display_string("1.ATM 2.PayWave", 1)
    lcd.lcd_display_string(f"Tot:${total:.2f} *=Back"[:16], 2)

def show_atm_prompt(lcd, pin_len):
    lcd.lcd_clear()
    lcd.lcd_display_string("Enter PIN:", 1)
    lcd.lcd_display_string(("*" * pin_len + "_" * (4 - pin_len))[:16], 2)

def show_paywave_prompt(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Tap RFID Card", 1)
    lcd.lcd_display_string("*=Back", 2)

def show_payment_ok(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Payment", 1)
    lcd.lcd_display_string("SUCCESS", 2)

def show_payment_fail(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Payment", 1)
    lcd.lcd_display_string("FAILED", 2)

def show_wrong_pin(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Wrong PIN", 1)
    lcd.lcd_display_string("Try Again", 2)

# ==============================
# INPUT HELPERS
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

        # Accept int digits OR string digits
        if (isinstance(k, int) and 0 <= k <= 9) or (isinstance(k, str) and k.isdigit()):
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
# MAIN
# ==============================
def main():
    current_state = STATE_MENU_1
    cart_total = 0.0
    cart = {}
    last_key_time = time.time()

    # HAL init
    led.init()
    adc.init()
    buzzer.init()
    moisture_sensor.init()
    input_switch.init()
    ir_sensor.init()
    rfid = rfid_reader.init()
    servo.init()
    usonic.init()
    dc_motor.init()
    accel.init()

    keypad.init(key_pressed)
    Thread(target=keypad.get_key, daemon=True).start()

    lcd = LCD.lcd()

    # Camera init
    try:
        scanner = BarcodeScanner(show_preview=True)
        scanner_ok = True
    except Exception as e:
        print("[ERROR] Scanner init failed:", e, flush=True)
        scanner = None
        scanner_ok = False

    # Boot only if switch is ON; else show shutdown
    if input_switch.read_slide_switch() == 0:
        show_shutdown(lcd)
        wait_for_switch_on(lcd)

    menu.startup_screen(lcd)
    menu.menu_page_1(lcd, scanner_ok)

    while True:
        # Master switch check
        if input_switch.read_slide_switch() == 0:
            show_shutdown(lcd)
            wait_for_switch_on(lcd)
            current_state = STATE_MENU_1
            cart_total = 0.0
            cart = {}
            menu.menu_page_1(lcd, scanner_ok)
            last_key_time = time.time()
            continue

        # Menu inactivity refresh
        if time.time() - last_key_time > 30 and current_state == STATE_MENU_1:
            menu.menu_page_1(lcd, scanner_ok)
            last_key_time = time.time()

        # Keypad read
        try:
            keyvalue = shared_keypad_queue.get(timeout=0.1)
            last_key_time = time.time()
        except queue.Empty:
            keyvalue = None

        # Debug (optional)
        # if keyvalue is not None:
        #     print("DEBUG state:", current_state, "key:", keyvalue, "type:", type(keyvalue), flush=True)

        # '*' global back
        if keyvalue == "*":
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd, scanner_ok)
            continue

        # ==============================
        # MENU PAGE 1
        # ==============================
        if current_state == STATE_MENU_1 and keyvalue is not None:
            if keyvalue in (1, "1"):
                current_state = STATE_ONLINE_PICKUP
                show_online_pickup_page(lcd)
                continue

            if keyvalue in (2, "2"):
                cart_total = 0.0
                cart = {}
                current_state = STATE_IN_STORE
                show_in_store_page(lcd, cart_total)
                continue

            menu.invalid_input(lcd)
            menu.menu_page_1(lcd, scanner_ok)
            continue

        # ==============================
        # ONLINE PICKUP (QR)
        # ==============================
        if current_state == STATE_ONLINE_PICKUP:
            if not scanner_ok or scanner is None:
                menu.scanner_error(lcd)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_ok)
                continue

            show_online_pickup_page(lcd)
            qr = scanner.scan_once(timeout=2, mode="qr")
            if qr:
                qr = str(qr).strip()
                status, pickup_id = claim_pickup_by_qr(qr)

                if status == "OK":
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Order {pickup_id}"[:16], 1)
                    lcd.lcd_display_string("Collected"[:16], 2)
                    buzzer.beep(0.2, 0, 1)
                    time.sleep(2)

                elif status == "ALREADY":
                    blink_error_led()
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Order Collected"[:16], 1)
                    lcd.lcd_display_string("Already Error"[:16], 2)
                    time.sleep(2)

                elif status == "INVALID":
                    blink_error_led()
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Invalid QR", 1)
                    lcd.lcd_display_string("Call Staff", 2)
                    time.sleep(2)

                else:
                    blink_error_led()
                    lcd.lcd_clear()
                    lcd.lcd_display_string("DB Offline", 1)
                    lcd.lcd_display_string("Call Staff", 2)
                    time.sleep(2)

                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_ok)

            continue

        # ==============================
        # IN-STORE BARCODE SCANNING
        # ==============================
        if current_state == STATE_IN_STORE:
            # '#' = Back when total=0, Pay when total>0
            if keyvalue == "#":
                if cart_total <= 0:
                    current_state = STATE_MENU_1
                    menu.menu_page_1(lcd, scanner_ok)
                else:
                    current_state = STATE_CHECKOUT
                    show_checkout_menu(lcd, cart_total)
                continue

            if not scanner_ok or scanner is None:
                menu.scanner_error(lcd)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_ok)
                continue

            show_in_store_page(lcd, cart_total)
            code = scanner.scan_once(timeout=2, mode="barcode")
            if code:
                code = str(code).strip()
                barcode10 = code.zfill(BARCODE_LEN)

                product = get_product_by_barcode(barcode10)
                if not product:
                    blink_error_led()
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

            continue

        # ==============================
        # CHECKOUT
        # ==============================
        if current_state == STATE_CHECKOUT and keyvalue is not None:
            if keyvalue in (1, "1"):
                current_state = STATE_ATM_PIN
                continue
            if keyvalue in (2, "2"):
                current_state = STATE_PAYWAVE
                show_paywave_prompt(lcd)
                continue
            continue

        # ==============================
        # ATM PIN
        # ==============================
        if current_state == STATE_ATM_PIN:
            pin = read_pin(shared_keypad_queue, lcd)
            if pin is None:
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            if pin != "1234":
                show_wrong_pin(lcd)
                time.sleep(2)
                current_state = STATE_CHECKOUT
                show_checkout_menu(lcd, cart_total)
                continue

            ok = deduct_stock_after_payment(cart)
            if not ok:
                blink_error_led()
                lcd.lcd_clear()
                lcd.lcd_display_string("Stock Issue", 1)
                lcd.lcd_display_string("Call Staff", 2)
                time.sleep(2)
                current_state = STATE_MENU_1
                cart_total = 0.0
                cart = {}
                menu.menu_page_1(lcd, scanner_ok)
                continue

            show_payment_ok(lcd)
            buzzer.beep(0.2, 0, 1)
            time.sleep(2)

            current_state = STATE_MENU_1
            cart_total = 0.0
            cart = {}
            menu.menu_page_1(lcd, scanner_ok)
            continue

        # ==============================
        # PAYWAVE (RFID)
        # ==============================
        if current_state == STATE_PAYWAVE:
            show_paywave_prompt(lcd)
            card = read_rfid_id(rfid)

            if card:
                card = str(card).strip()

                if card not in CARD_BALANCES:
                    blink_error_led()
                    show_payment_fail(lcd)
                    time.sleep(2)
                    current_state = STATE_CHECKOUT
                    show_checkout_menu(lcd, cart_total)
                    continue

                if CARD_BALANCES[card] < cart_total:
                    blink_error_led()
                    show_payment_fail(lcd)
                    time.sleep(2)
                    current_state = STATE_CHECKOUT
                    show_checkout_menu(lcd, cart_total)
                    continue

                ok = deduct_stock_after_payment(cart)
                if not ok:
                    blink_error_led()
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Stock Issue", 1)
                    lcd.lcd_display_string("Call Staff", 2)
                    time.sleep(2)
                    current_state = STATE_MENU_1
                    cart_total = 0.0
                    cart = {}
                    menu.menu_page_1(lcd, scanner_ok)
                    continue

                # Deduct balance (demo)
                CARD_BALANCES[card] -= cart_total

                show_payment_ok(lcd)
                buzzer.beep(0.2, 0, 1)
                time.sleep(2)

                current_state = STATE_MENU_1
                cart_total = 0.0
                cart = {}
                menu.menu_page_1(lcd, scanner_ok)
                continue

            # timeout / no card -> back to checkout
            current_state = STATE_CHECKOUT
            show_checkout_menu(lcd, cart_total)
            continue

if __name__ == "__main__":
    main()