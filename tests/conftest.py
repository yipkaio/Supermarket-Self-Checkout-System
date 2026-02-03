import sys
from unittest.mock import MagicMock

# Mock hardware-only modules
sys.modules["hal"] = MagicMock()
sys.modules["hal.hal_lcd"] = MagicMock()
sys.modules["hal.hal_buzzer"] = MagicMock()
sys.modules["hal.hal_keypad"] = MagicMock()
sys.modules["hal.hal_rfid_reader"] = MagicMock()
sys.modules["barcode_scanner"] = MagicMock()

# Allow src imports
import os
sys.path.insert(0, os.path.abspath("src"))
