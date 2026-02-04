# barcode_scanner.py
import time
import cv2
from picamera2 import Picamera2
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol 

class BarcodeScanner:
    def __init__(self, frame_size=(640, 480), show_preview=True):
        self.show_preview = show_preview

        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"format": "BGR888", "size": frame_size}
        )
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(1)

        self.last_code = None
        self.last_time = 0.0
        self._last_heartbeat = 0.0

    def scan_once(self, timeout=10, debounce_seconds=2.0, mode="barcode"):
        """
        mode:
          - "barcode" → product barcodes only
          - "qr"      → QR codes only
        """
        start = time.time()

        # Select symbols based on mode
        if mode == "qr":
            symbols = [ZBarSymbol.QRCODE]
        else:
            # barcode-only symbols (skip any missing ones to avoid crash)
            wanted = ["EAN13", "EAN8", "CODE128", "CODE39", "UPCA", "UPCE"]
            symbols = [getattr(ZBarSymbol, s) for s in wanted if hasattr(ZBarSymbol, s)]

        while time.time() - start < timeout:
            frame = self.picam2.capture_array()

            # heartbeat every 1s
            now = time.time()
            if now - self._last_heartbeat >= 1.0:
                print(f"[DEBUG] scanning ({mode})...", flush=True)
                self._last_heartbeat = now

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)

            codes = pyzbar.decode(gray, symbols=symbols)

            # draw debug boxes
            if self.show_preview:
                for c in codes:
                    x, y, w, h = c.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    txt = c.data.decode("utf-8", errors="ignore").strip()
                    cv2.putText(
                        frame, txt, (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                    )

                cv2.imshow("Scanner Debug Preview (press q to close)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    return None

            for c in codes:
                code = c.data.decode("utf-8", errors="ignore").strip()
                t = time.time()

                # debounce
                if code == self.last_code and (t - self.last_time) < debounce_seconds:
                    continue

                self.last_code = code
                self.last_time = t

                print(f"[SCANNED-{mode.upper()}]", code, flush=True)
                return code

            time.sleep(0.02)

        return None

    def close(self):
        try:
            self.picam2.stop()
        except Exception:
            pass

        if self.show_preview:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
