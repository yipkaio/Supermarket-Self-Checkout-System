import menu

class FakeLCD:
    """
    Fake LCD object to capture display output for testing.
    """
    def __init__(self):
        self.lines = {}
        self.cleared = 0

    def lcd_clear(self):
        self.lines = {}
        self.cleared += 1

    def lcd_display_string(self, text, line):
        self.lines[line] = text


def test_startup_screen(monkeypatch):
    # Remove delay during testing
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.startup_screen(lcd)

    assert lcd.cleared >= 1
    assert "Loading" in lcd.lines.get(1, "")


def test_menu_page_1_scanner_available():
    lcd = FakeLCD()
    menu.menu_page_1(lcd, scanner_available=True)

    assert "Online" in lcd.lines.get(1, "")
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
    assert "Try" in lcd.lines.get(2, "")


def test_keypad_error(monkeypatch):
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.keypad_error(lcd)

    assert "Keypad" in lcd.lines.get(1, "")
    assert "Restart" in lcd.lines.get(2, "")


def test_scanner_error(monkeypatch):
    monkeypatch.setattr(menu.time, "sleep", lambda *_: None)

    lcd = FakeLCD()
    menu.scanner_error(lcd)

    assert "Scanner" in lcd.lines.get(1, "")
    assert "Unavailable" in lcd.lines.get(2, "")
