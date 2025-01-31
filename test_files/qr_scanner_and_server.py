import threading
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
import cv2
import numpy as np
import mariadb
import app  # Import the Flask app module

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialize the PiCamera2
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(video_config)

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

# Database connection function
def get_db_connection():
    return mariadb.connect(
        user="root",
        password="",
        host="localhost",
        database="vending_machine"
    )

print("QR Code Scanner with Optimized Preview. Waiting for switch to be turned on...")

# Function to run the Flask app
def run_flask_app():
    app.app.run(host="0.0.0.0", port=5000, use_reloader=False)

# Start Flask app in a separate thread
flask_thread = threading.Thread(target=run_flask_app)
flask_thread.daemon = True
flask_thread.start()

try:
    while True:
        if scanning:
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
                    try:
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT drink_type FROM purchases WHERE purchase_id=?", (qr_data,))
                            result = cur.fetchone()
                            if result:
                                print(f"Drink type: {result[0]}")
                                # Add logic to dispense the drink
                            else:
                                print("Purchase not found")
                    except mariadb.Error as e:
                        print(f"Database error: {e}")

                    # Draw rectangle around the QR code
                    points = np.array([code.polygon], np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [points], isClosed=True, color=(0, 255, 0), thickness=2)

                    # Display QR code data as text
                    if code.polygon:
                        x, y = code.polygon[0].x, code.polygon[0].y
                        cv2.putText(frame, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Display the frame in a preview window
                cv2.imshow("QR Code Scanner", frame)

                # Exit if the user presses 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    scanning = False

            picam2.stop()
            cv2.destroyAllWindows()
            print("QR Code Scanner stopped. Waiting for switch to be turned on again...")

except KeyboardInterrupt:
    print("\nExiting...")

# Cleanup
GPIO.cleanup()
print("GPIO cleaned up.")