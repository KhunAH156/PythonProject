import os
import time
import cv2
import requests
import mariadb
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from pyzbar.pyzbar import decode

# Database Connection
conn = mariadb.connect(
    user="root",
    password="",
    host="localhost",
    database="smart_door_lock"
)
cur = conn.cursor()

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "7723998968:AAFc4QK-qRaIxCfqeqLYRs1OLuF-2z_OOiM"
TELEGRAM_CHAT_ID = "5819192033"

# Folder to save videos
VIDEO_FOLDER = "videos"
os.makedirs(VIDEO_FOLDER, exist_ok=True)  # Ensure folder exists


def is_camera_in_use():
    """Check if another process is using the camera."""
    return "picamera2" in os.popen("ps aux | grep picamera2 | grep -v grep").read()


def scan_qr(scan_time=20):
    """Scans a QR code and checks the database."""
    if is_camera_in_use():
        print("Camera is already in use by another process.")
        return False

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)

    scanning = True
    qr_detected = False
    start_time = time.time()

    picam2.start()
    print("QR Scanner started...")

    while scanning:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        codes = decode(gray)

        for code in codes:
            qr_data = code.data.decode("utf-8")
            print(f"QR Code Detected: {qr_data}")

            cur.execute("SELECT id FROM TemporaryQR WHERE key_id=?", (qr_data,))
            result = cur.fetchone()
            if result:
                cur.execute("DELETE FROM TemporaryQR WHERE key_id=?", (qr_data,))
                conn.commit()
                os.remove(f"static/qrcodes/{qr_data}.png")
                scanning = False
                qr_detected = True
                break

        cv2.imshow("QR Code Scanner", frame)

        if time.time() - start_time > scan_time:
            print("Scanning time exceeded.")
            scanning = False

        if cv2.waitKey(1) & 0xFF == ord('q'):
            scanning = False

    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()

    return qr_detected


def record_and_send_video():
    """Records a 10-second video and sends it via Telegram."""
    if is_camera_in_use():
        print("Camera is already in use by another process.")
        return

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)
    encoder = H264Encoder(bitrate=5000000)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.h264")
    mp4_path = output.replace(".h264", ".mp4")

    try:
        print(f"Recording video: {output}")
        picam2.start_recording(encoder, output)
        time.sleep(10)
        picam2.stop_recording()
        print("Recording complete.")

        print("Converting video to MP4...")
        os.system(f"ffmpeg -i {output} -c copy {mp4_path} -y")
        print("Conversion complete.")

        send_telegram_video(mp4_path)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        picam2.close()


def send_telegram_video(video_path):
    """Sends the recorded video via Telegram Bot."""
    print(f"Sending video: {video_path}")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    
    with open(video_path, "rb") as video_file:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"video": video_file})
    
    if response.status_code == 200:
        print("Video sent successfully.")
    else:
        print(f"Failed to send video: {response.text}")
