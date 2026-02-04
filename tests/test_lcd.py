import sys
from types import SimpleNamespace

# Fake pymysql so importing main.py won't crash on Windows
sys.modules["pymysql"] = SimpleNamespace(
    MySQLError=Exception,
    connect=lambda *a, **k: None
)

import main


class FakeLCD:
    """Fake LCD to capture display output"""
    def __init__(self):
        self.lines = {}
        self.cleared = 0

    def lcd_clear(self):
        self.lines = {}
        self.cleared += 1

    def lcd_display_string(self, text, line):
        self.lines[line] = text


def test_show_online_pickup_page():
    lcd = FakeLCD()
    main.show_online_pickup_page(lcd)

    assert "Online" in lcd.lines.get(1, "")
    assert "Scan" in lcd.lines.get(2, "")


def test_show_checkout_menu():
    lcd = FakeLCD()
    main.show_checkout_menu(lcd, total=12.50)

    assert "ATM" in lcd.lines.get(1, "")
    assert "Tot" in lcd.lines.get(2, "")


def test_show_atm_prompt_zero_digits():
    lcd = FakeLCD()
    main.show_atm_prompt(lcd, pin_len=0)

    assert "Enter PIN" in lcd.lines.get(1, "")
    assert "_" in lcd.lines.get(2, "")


def test_show_atm_prompt_two_digits():
    lcd = FakeLCD()
    main.show_atm_prompt(lcd, pin_len=2)

    assert "**" in lcd.lines.get(2, "")


def test_show_paywave_prompt():
    lcd = FakeLCD()
    main.show_paywave_prompt(lcd)

    assert "Tap" in lcd.lines.get(1, "")
    assert "Back" in lcd.lines.get(2, "")


def test_show_payment_ok():
    lcd = FakeLCD()
    main.show_payment_ok(lcd)

    assert "Payment" in lcd.lines.get(1, "")
    assert "SUCCESS" in lcd.lines.get(2, "")


def test_show_payment_fail():
    lcd = FakeLCD()
    main.show_payment_fail(lcd)

    assert "Payment" in lcd.lines.get(1, "")
    assert "FAILED" in lcd.lines.get(2, "")


def test_show_wrong_pin():
    lcd = FakeLCD()
    main.show_wrong_pin(lcd)

    assert "Wrong PIN" in lcd.lines.get(1, "")
    assert "Try" in lcd.lines.get(2, "")