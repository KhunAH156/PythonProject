import time
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
import cv2
import numpy as np
import mariadb


# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialize the PiCamera2
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(video_config)

# Connect to MariaDB
conn = mariadb.connect(
    user="root",
    password="",
    host="localhost",
    database="smart_door_lock"
)
cur = conn.cursor()

# Flag to control the QR code scanning
scanning = False


def switch_callback(channel):
    global scanning
    if GPIO.input(22) == GPIO.HIGH:
        print("Switch is ON. Starting QR Code Scanner. Press 'q' to quit.")
        scanning = True
    else:
        print("Switch is OFF. Stopping QR Code Scanner.")
        scanning = False

# Add event detection for the switch
GPIO.add_event_detect(22, GPIO.BOTH, callback=switch_callback, bouncetime=300)

def scan_qr(scan_time=20):
    """Scan QR code and return the drink type."""
    scanning = True
    QrOk = False
    start_time = time.time()

    # Start the camera
    picam2.start()

    while scanning:
        # Capture a frame from the camera
        frame = picam2.capture_array()

        # Convert the frame to grayscale for faster QR code processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect QR codes
        codes = decode(gray)

        # Draw bounding boxes and show QR data
        for code in codes:
            qr_data = code.data.decode("utf-8")
            print(f"QR Code Detected: {qr_data}")

            # Query the database for the purchase_id and retrieve drink_type
            cur.execute("SELECT id FROM TemporaryQR WHERE key_id=?", (qr_data,))
            result = cur.fetchone()
            if result:
                
                # Delete the row from the database so the QR code can't be reused
                cur.execute("DELETE FROM TemporaryQR WHERE key_id=?", (qr_data,))
                conn.commit()
                scanning = False
                QrOk = True
                break

        # Display the frame in a preview window
        cv2.imshow("QR Code Scanner", frame)

        # Stop scanning if the time limit is exceeded
        if time.time() - start_time > scan_time:
            print("Scanning time exceeded.")
            scanning = False

        # Exit if the user presses 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            scanning = False

    picam2.stop()
    cv2.destroyAllWindows()

    if QrOk:
        return True
    else:
        return False


if __name__ == "__main__":
    # Start scanning
    scan_qr(scan_time=20)
