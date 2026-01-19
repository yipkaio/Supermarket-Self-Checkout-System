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
    print("KEY PRESSED:", key)  # keep debug for now
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
    lcd.lcd_display_string("Scan Item", 1)
    lcd.lcd_display_string("# to Finish", 2)

def show_admin_login_page(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Admin Login", 1)
    lcd.lcd_display_string("Enter PIN", 2)

# ==============================
# Helper for invalid handling (REQ-07/08)
# ==============================
def handle_invalid(lcd, current_state, scanner_available, invalid_count):
    """
    REQ-07: show invalid input message (2s) and return to current menu/page
    REQ-08: after 3 invalid inputs -> keypad error -> restart system (REQ-01)
    Returns: (new_state, new_invalid_count, restarted_bool)
    """
    invalid_count += 1
    menu.invalid_input(lcd)

    if invalid_count >= 3:
        # REQ-08
        menu.keypad_error(lcd)
        menu.startup_screen(lcd)      # restart (REQ-01)
        menu.menu_page_1(lcd, scanner_available)
        return (STATE_MENU_1, 0, True)

    # Return user to the correct screen after invalid input
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

    # REQ-09: scanner availability flag (set False if scanner fails)
    # For now, keep True unless you detect failure later.
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
            continue

        # REQ-06 '*' anytime -> menu page 1
        if keyvalue == "*":
            current_state = STATE_MENU_1
            invalid_count = 0
            menu.menu_page_1(lcd, scanner_available)
            continue

        # REQ-04 '#' toggle menu pages; if in other states, treat as back to menu
        if keyvalue == "#":
            invalid_count = 0
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
        # Handle according to current state
        # ==============================

        # MENU PAGE 1 (REQ-02)
        if current_state == STATE_MENU_1:
            if keyvalue == 1:
                if not scanner_available:
                    # REQ-09: online pickup disabled
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

        # MENU PAGE 2 (REQ-03)
        if current_state == STATE_MENU_2:
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

        # OTHER STATES (placeholders)
        # If user presses unexpected keys here, count as invalid attempt
        current_state, invalid_count, _ = handle_invalid(
            lcd, current_state, scanner_available, invalid_count
        )

if __name__ == "__main__":
    main()
