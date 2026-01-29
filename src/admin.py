import time
import subprocess
from hal import hal_lcd as LCD
from hal import hal_keypad as keypad

# ==============================
# Constants (REQ-42)
# ==============================
ADMIN_PIN = "1234"
AUTO_LOCK_TIME = 60  # seconds

# ==============================
# Globals
# ==============================
lcd = LCD.lcd()
lcd.lcd_clear()

last_activity_time = time.time()
entered_pin = ""

# ==============================
# RESET TIMER (REQ-47)
# ==============================
def reset_timer():
    global last_activity_time
    last_activity_time = time.time()

# ==============================
# CHECK AUTO LOCK (REQ-47)
# ==============================
def check_auto_lock():
    if time.time() - last_activity_time > AUTO_LOCK_TIME:
        lcd.lcd_clear()
        lcd.lcd_display_string("Session Locked", 1)
        time.sleep(2)
        return True
    return False

# ==============================
# ADMIN LOGIN (REQ-43)
# ==============================
def admin_login():
    global entered_pin
    entered_pin = ""
    reset_timer()

    lcd.lcd_clear()
    lcd.lcd_display_string("Enter Admin Pin", 1)
    lcd.lcd_display_string("Press # to Enter", 2)

    while True:
        if check_auto_lock():
            return

        key = keypad.get_key()
        if key:
            reset_timer()

            if key == "#":
                if entered_pin == ADMIN_PIN:
                    admin_menu()
                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Wrong PIN", 1)
                    time.sleep(2)
                return

            elif key == "*":
                return

            elif key.isdigit() and len(entered_pin) < 4:
                entered_pin += key
                lcd.lcd_display_string(" " * 16, 2)
                lcd.lcd_display_string("*" * len(entered_pin), 2)

# ==============================
# ADMIN MENU (REQ-44)
# ==============================
def admin_menu():
    reset_timer()
    lcd.lcd_clear()
    lcd.lcd_display_string("1.Stock Mgmt", 1)
    lcd.lcd_display_string("2.System Logs", 2)

    while True:
        if check_auto_lock():
            return

        key = keypad.get_key()
        if key:
            reset_timer()

            if key == "1":
                lcd.lcd_clear()
                lcd.lcd_display_string("Opening Stock", 1)
                time.sleep(1)

                subprocess.run(["python3", "stock_mgmt.py"])

                lcd.lcd_clear()
                lcd.lcd_display_string("1.Stock Mgmt", 1)
                lcd.lcd_display_string("2.System Logs", 2)

            elif key == "2":
                lcd.lcd_clear()
                lcd.lcd_display_string("Opening Logs", 1)
                time.sleep(1)

                subprocess.run(["python3", "stocklogs.py"])

                lcd.lcd_clear()
                lcd.lcd_display_string("1.Stock Mgmt", 1)
                lcd.lcd_display_string("2.System Logs", 2)

            elif key == "*":
                return

# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    admin_login()

