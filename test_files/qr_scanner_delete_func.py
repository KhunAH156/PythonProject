import cv2
import numpy as np
from pyzbar.pyzbar import decode
from picamera2 import Picamera2
import mariadb
import threading

# Shared variables
running = threading.Event()
drink_type = None
drink_type_lock = threading.Lock()

# Database and camera setup
conn = mariadb.connect(
    user="root",
    password="",
    host="localhost",
    database="vending_machine"
)
cur = conn.cursor()

picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(video_config)

def qr_code_scanner():
    """Function to run the QR code scanner."""
    global running, drink_type

    print("QR Code Scanner thread started.")
    picam2.start()

    while running.is_set():
        # Capture a frame from the camera
        frame = picam2.capture_array()

        # Convert the frame to grayscale for faster QR code processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect QR codes
        codes = decode(gray)

        # Process each detected QR code
        for code in codes:
            qr_data = code.data.decode("utf-8")
            print(f"QR Code Detected: {qr_data}")

            # Query the database for the purchase_id and retrieve drink_type
            cur.execute("SELECT drink_type FROM purchases WHERE purchase_id=?", (qr_data,))
            result = cur.fetchone()
            if result:
                with drink_type_lock:
                    drink_type = result[0]
                    print(f"Drink type: {drink_type}")

                # Delete the processed row from the database
                cur.execute("DELETE FROM purchases WHERE purchase_id=?", (qr_data,))
                conn.commit()
                print(f"Row with purchase_id {qr_data} removed from the database.")

                # Stop scanning after processing the valid QR code
                running.clear()  # Stop the loop
                return

        # Show the preview for the QR code scanner
        cv2.imshow("QR Code Scanner", frame)

        # Exit the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running.clear()

    print("QR Code Scanner stopped.")
    picam2.stop()
    cv2.destroyAllWindows()

def start_scanner():
    """Start the QR code scanner."""
    running.set()  # Start the scanner loop

def stop_scanner():
    """Stop the QR code scanner."""
    running.clear()  # Stop the scanner loop