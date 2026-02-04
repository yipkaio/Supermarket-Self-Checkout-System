import time


# REQ-01 : System Startup

def startup_screen(lcd):
    """
    On power ON, LCD displays 'Loading..' for 2 seconds
    """
    lcd.lcd_clear()
    lcd.lcd_display_string("Loading..", 1)
    time.sleep(2)



# REQ-02 : Main Menu Page 1

def menu_page_1(lcd, scanner_available=True):
    """
    Display Main Menu Page 1
    """
    lcd.lcd_clear()

    if scanner_available:
        lcd.lcd_display_string("1.Online Pickup", 1)
    else:
        lcd.lcd_display_string("1.Unavailable", 1)

    lcd.lcd_display_string("2.In-Store", 2)






# REQ-07 : Invalid Input

def invalid_input(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Invalid Input", 1)
    lcd.lcd_display_string("Try Again", 2)
    time.sleep(2)



# REQ-08 : Keypad Error

def keypad_error(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Keypad Error", 1)
    lcd.lcd_display_string("Restarting", 2)
    time.sleep(1)



# REQ-09 : Scanner Error

def scanner_error(lcd):
    lcd.lcd_clear()
    lcd.lcd_display_string("Scanner Error", 1)
    lcd.lcd_display_string("Unavailable", 2)
    time.sleep(1)
