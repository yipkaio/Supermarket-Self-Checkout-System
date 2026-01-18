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
# Menu States (REQ-04)
# ==============================
STATE_MENU_1 = 1
STATE_MENU_2 = 2
current_state = STATE_MENU_1

# REQ-05 inactivity tracking
last_key_time = time.time()

shared_keypad_queue = queue.Queue()


# ==============================
# Keypad callback
# ==============================
def key_pressed(key):
    shared_keypad_queue.put(key)


def main():
    global current_state, last_key_time

    # ==============================
    # HAL Initialisation
    # ==============================
    led.init()
    adc.init()
    buzzer.init()
    moisture_sensor.init()
    input_switch.init()
    ir_sensor.init()
    reader = rfid_reader.init()
    servo.init()
    temp_humid_sensor.init()
    usonic.init()
    dc_motor.init()
    accelerometer = accel.init()

    keypad.init(key_pressed)
    Thread(target=keypad.get_key, daemon=True).start()

    lcd = LCD.lcd()
    lcd.lcd_clear()

    # ==============================
    # REQ-01 System Startup
    # ==============================
    menu.startup_screen(lcd)

    # REQ-02 Initial Menu
    menu.menu_page_1(lcd)

    # ==============================
    # Main Loop
    # ==============================
    while True:

        # ==============================
        # REQ-05 : 30s inactivity reset
        # ==============================
        if time.time() - last_key_time > 30:
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd)

        # ==============================
        # Non-blocking keypad read
        # ==============================
        try:
            keyvalue = shared_keypad_queue.get(timeout=0.1)
            last_key_time = time.time()
        except queue.Empty:
            continue

        # ==============================
        # REQ-06 : '*' anytime → Menu 1
        # ==============================
        if keyvalue == "*":
            current_state = STATE_MENU_1
            menu.menu_page_1(lcd)
            continue

        # ==============================
        # REQ-04 : '#' menu navigation
        # ==============================
        if keyvalue == "#":
            if current_state == STATE_MENU_1:
                current_state = STATE_MENU_2
                menu.menu_page_2(lcd)
            else:
                current_state = STATE_MENU_1
                menu.menu_page_1(lcd)
            continue

        # ==================================================
        # Diagnostic / Functional Logic (unchanged)
        # ==================================================
        if keyvalue == 1:
            lcd.lcd_clear()
            lcd.lcd_display_string("LED TEST", 1)
            led.set_output(1, 1)
            time.sleep(2)
            led.set_output(1, 0)

        elif keyvalue == 2:
            lcd.lcd_clear()
            val = adc.get_adc_value(1)
            lcd.lcd_display_string("Pot " + str(val), 1)

        elif keyvalue == 3:
            lcd.lcd_clear()
            lcd.lcd_display_string("Buzzer TEST", 1)
            buzzer.beep(0.5, 0.5, 1)

        elif keyvalue == 4:
            lcd.lcd_clear()
            val = moisture_sensor.read_sensor()
            lcd.lcd_display_string("Moisture", 1)
            lcd.lcd_display_string(str(val), 2)

        elif keyvalue == 5:
            lcd.lcd_clear()
            dist = usonic.get_distance()
            lcd.lcd_display_string("Distance", 1)
            lcd.lcd_display_string(str(dist), 2)

        elif keyvalue == 6:
            lcd.lcd_clear()
            card_id = reader.read_id_no_block()
            if card_id:
                lcd.lcd_display_string("RFID ID", 1)
                lcd.lcd_display_string(str(card_id), 2)
            else:
                menu.scanner_error(lcd)

        elif keyvalue == 7:
            lcd.lcd_clear()
            ldr = adc.get_adc_value(0)
            lcd.lcd_display_string("LDR", 1)
            lcd.lcd_display_string(str(ldr), 2)

        elif keyvalue == 8:
            lcd.lcd_clear()
            lcd.lcd_display_string("Servo / DC", 1)
            servo.set_servo_position(90)
            dc_motor.set_motor_speed(50)
            time.sleep(2)
            dc_motor.set_motor_speed(0)

        elif keyvalue == 9:
            lcd.lcd_clear()
            t, h = temp_humid_sensor.read_temp_humidity()
            lcd.lcd_display_string("T:" + str(t), 1)
            lcd.lcd_display_string("H:" + str(h), 2)

        else:
            # REQ-07 Invalid input
            menu.invalid_input(lcd)


if __name__ == "__main__":
    main()
