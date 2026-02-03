# tests/test_menu.py
import menu

class FakeLCD:
    """
    Simple LCD stub to capture what was displayed.
    """
    def __init__(self):
        self.lines = {}

    def lcd_clear(self):
        self.lines = {}

    def lcd_display_string(self, text, line):
        self.lines[line] = text

def test_startup_screen(monkeypatch):
    # avoid waiting in tests
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.startup_screen(lcd)

    assert lcd.lines.get(1) == "Loading.."

def test_menu_page_1_scanner_available():
    lcd = FakeLCD()
    menu.menu_page_1(lcd, scanner_available=True)

    assert "Online Pickup" in lcd.lines.get(1, "")
    assert "In-Store" in lcd.lines.get(2, "")

def test_menu_page_1_scanner_unavailable():
    lcd = FakeLCD()
    menu.menu_page_1(lcd, scanner_available=False)

    assert "Unavailable" in lcd.lines.get(1, "")
    assert "In-Store" in lcd.lines.get(2, "")

def test_invalid_input(monkeypatch):
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.invalid_input(lcd)

    assert "Invalid" in lcd.lines.get(1, "")
    assert "Try Again" in lcd.lines.get(2, "")

def test_keypad_error(monkeypatch):
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.keypad_error(lcd)

    assert "Keypad Error" in lcd.lines.get(1, "")
    assert "Restart" in lcd.lines.get(2, "")

def test_scanner_error(monkeypatch):
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.scanner_error(lcd)

    assert "Scanner Error" in lcd.lines.get(1, "")
    assert "Unavailable" in lcd.lines.get(2, "")
