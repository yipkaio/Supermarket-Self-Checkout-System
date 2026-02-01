import time
from threading import Thread
import queue

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
from barcode_scanner import BarcodeScanner  # already in same folder

# ==============================
# States
# ==============================
STATE_MENU_1 = 1
STATE_MENU_2 = 2
STATE_ONLINE_PICKUP = 3
STATE_IN_STORE = 4
STATE_ADMIN_LOGIN = 5

shared_keypad_queue = queue.Queue()

# ==============================
# Keypad callback
# ==============================
def key_pressed(key):
    print("KEY PRESSED:", key, flush=True)
    shared_keypad_queue.put(key)

# ==============================
# Simple placeholder pages
# ==============================
def show_online_pickup_page(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Online Pickup", 1)
    lcd.lcd_display_string("Scan QR...", 2)

def show_in_store_page(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("In-Store Mode", 1)
    lcd.lcd_display_string("#=Finish *=Back", 2)

def show_admin_login_page(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Admin Login", 1)
    lcd.lcd_display_string("Enter PIN", 2)

# ==============================
# Helper for invalid handling (REQ-07/08)
# ==============================
def handle_invalid(lcd, current_state, scanner_available, invalid_count):
    invalid_count += 1
    menu.invalid_input(lcd)

    if invalid_count >= 3:
        menu.keypad_error(lcd)
        menu.startup_screen(lcd)
        menu.menu_page_1(lcd, scanner_available)
        return (STATE_MENU_1, 0, True)

    if current_state == STATE_MENU_1:
        menu.menu_page_1(lcd, scanner_available)
    elif current_state == STATE_MENU_2:
        menu.menu_page_2(lcd)
    elif current_state == STATE_ONLINE_PICKUP:
        show_online_pickup_page(lcd)
    elif current_state == STATE_IN_STORE:
        show_in_store_page(lcd)
    elif current_state == STATE_ADMIN_LOGIN:
        show_admin_login_page(lcd)

    return (current_state, invalid_count, False)

def main():
    # ==============================
    # Variables
    # ==============================
    current_state = STATE_MENU_1
    last_key_time = time.time()
    invalid_count = 0

    # REQ-09 scanner availability flag
    scanner_available = True

    # ==============================
    # HAL init
    # ==============================
    led.init()
    adc.init()
    buzzer.init()
    moisture_sensor.init()
    input_switch.init()
    ir_sensor.init()
    rfid_reader.init()
    servo.init()
    temp_humid_sensor.init()
    usonic.init()
    dc_motor.init()
    accel.init()

    keypad.init(key_pressed)
    Thread(target=keypad.get_key, daemon=True).start()

    lcd = LCD.lcd()
    lcd.lcd_clear()

    # ==============================
    # Create barcode scanner ONCE (debug preview on VNC)
    # ==============================
    scanner = None
    try:
        scanner = BarcodeScanner(show_preview=True)
        scanner_available = True
        print("[INFO] BarcodeScanner initialized", flush=True)
    except Exception as e:
        scanner_available = False
        print("[ERROR] BarcodeScanner failed:", e, flush=True)

    # REQ-01 startup
    menu.startup_screen(lcd)

    # REQ-02 main menu page 1
    current_state = STATE_MENU_1
    menu.menu_page_1(lcd, scanner_available)
    last_key_time = time.time()

    while True:
        # REQ-05 inactivity -> menu page 1
        if time.time() - last_key_time > 30:
            if current_state != STATE_MENU_1:
                current_state = STATE_MENU_1
                invalid_count = 0
                menu.menu_page_1(lcd, scanner_available)

        # Non-blocking keypad read
        try:
            keyvalue = shared_keypad_queue.get(timeout=0.1)
            last_key_time = time.time()
        except queue.Empty:
            # If we are in In-Store, we want to keep scanning even without keypad input
            keyvalue = None

        # REQ-06 '*' anytime -> menu page 1
        if keyvalue == "*":
            current_state = STATE_MENU_1
            invalid_count = 0
            menu.menu_page_1(lcd, scanner_available)
            continue

        # REQ-04 '#' toggle menu pages; if in other states, treat as back/finish
        if keyvalue == "#":
            invalid_count = 0
            if current_state == STATE_IN_STORE:
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)
                continue

            if current_state == STATE_MENU_1:
                current_state = STATE_MENU_2
                menu.menu_page_2(lcd)
            elif current_state == STATE_MENU_2:
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)
            else:
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)
            continue

        # ==============================
        # MENU PAGE 1
        # ==============================
        if current_state == STATE_MENU_1 and keyvalue is not None:
            if keyvalue == 1:
                if not scanner_available:
                    menu.scanner_error(lcd)
                    menu.menu_page_1(lcd, scanner_available)
                    continue

                invalid_count = 0
                current_state = STATE_ONLINE_PICKUP
                show_online_pickup_page(lcd)
                continue

            elif keyvalue == 2:
                invalid_count = 0
                current_state = STATE_IN_STORE
                show_in_store_page(lcd)
                continue

            else:
                current_state, invalid_count, _ = handle_invalid(
                    lcd, current_state, scanner_available, invalid_count
                )
                continue

        # ==============================
        # MENU PAGE 2
        # ==============================
        if current_state == STATE_MENU_2 and keyvalue is not None:
            if keyvalue == 3:
                invalid_count = 0
                current_state = STATE_ADMIN_LOGIN
                show_admin_login_page(lcd)
                continue
            else:
                current_state, invalid_count, _ = handle_invalid(
                    lcd, current_state, scanner_available, invalid_count
                )
                continue

        # ==============================
        # IN-STORE MODE: AUTO SCAN LOOP
        # ==============================
        if current_state == STATE_IN_STORE:
            if not scanner_available or scanner is None:
                menu.scanner_error(lcd)
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd, scanner_available)
                continue

            # Keep scanning continuously while in this state
            lcd.lcd_clear()
            lcd.lcd_display_string("Scanning...", 1)
            lcd.lcd_display_string("#=Finish *=Back", 2)

            code = scanner.scan_once(timeout=2)  # short timeout, loops again quickly
            if code:
                print("BARCODE SCANNED:", code, flush=True)
                lcd.lcd_clear()
                lcd.lcd_display_string("Scanned:", 1)
                lcd.lcd_display_string(code[:16], 2)
                buzzer.beep(0.2, 0.0, 1)
                time.sleep(1.5)
                show_in_store_page(lcd)

            # loop continues; user can press # or * anytime
            continue

        # ==============================
        # OTHER STATES (placeholders)
        # ==============================
        if keyvalue is not None:
            current_state, invalid_count, _ = handle_invalid(
                lcd, current_state, scanner_available, invalid_count
            )

if __name__ == "__main__":
    main()
