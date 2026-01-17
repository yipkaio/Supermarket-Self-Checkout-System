import time

# REQ-01 : System Startup

def startup_screen(lcd):
    """
    REQ-01
    On power ON, LCD displays 'Loading..' for 2 seconds
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("Loading..", 1)
    time.sleep(2)



# REQ-02 : Main Menu Page 1

def menu_page_1(lcd, scanner_available=True):
    """
    REQ-02 & REQ-09
    Display Main Menu Page 1.
    Online Pickup option is disabled if scanner fails.
    """
    lcd.lcd_clear()

    if scanner_available:
        lcd.lcd_display_string("1.Online Pickup", 1)
    else:
        lcd.lcd_display_string("1.Unavailable", 1)

    lcd.lcd_display_string("2.In-Store (#)", 2)



# REQ-03 : Main Menu Page 2

def menu_page_2(lcd):
    """
    REQ-03
    Display Admin menu page
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("3.Admin Login", 1)
    lcd.lcd_display_string("#.Back", 2)



# REQ-07 : Invalid Input

def invalid_input(lcd):
    """
    REQ-07
    Display invalid input message for 2 seconds
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("Invalid Input", 1)
    lcd.lcd_display_string("Try Again", 2)
    time.sleep(2)



# REQ-08 : Keypad Error

def keypad_error(lcd):
    """
    REQ-08
    Display keypad error and restart message
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("Keypad Error", 1)
    lcd.lcd_display_string("Restarting...", 2)
    time.sleep(2)


# ==================================================
# REQ-09 : Scanner Error
# ==================================================
def scanner_error(lcd):
    """
    REQ-09
    Display scanner unavailable message
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("Scanner Error", 1)
    lcd.lcd_display_string("Unavailable", 2)
    time.sleep(2)
