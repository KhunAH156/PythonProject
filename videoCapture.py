import os
import time
import requests
from picamera2 import Picamera2

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "7723998968:AAFc4QK-qRaIxCfqeqLYRs1OLuF-2z_OOiM"
TELEGRAM_CHAT_ID = "5819192033"

# Folder to save videos
VIDEO_FOLDER = "videos"
os.makedirs(VIDEO_FOLDER, exist_ok=True)  # Ensure folder exists

def record_and_send_video():
    """Captures a 10-second video and sends it via Telegram."""
    picam2 = Picamera2()

    # Generate unique video filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.h264")
    mp4_path = video_path.replace(".h264", ".mp4")

    try:
        # ✅ Configure the camera for video recording
        video_config = picam2.create_video_configuration()
        picam2.configure(video_config)
        
        # ✅ Start the camera before recording
        picam2.start()
        time.sleep(1)  # Give the camera time to warm up

        print(f"Recording video: {video_path}")
        picam2.start_recording(video_path, encode='h264')  # Pass filename and encode
        time.sleep(10)  # Record for 10 seconds
        picam2.stop_recording()
        print("Recording complete.")

        # Convert .h264 to .mp4 using ffmpeg
        print("Converting video to MP4...")
        os.system(f"ffmpeg -i {video_path} -c copy {mp4_path} -y")
        print("Conversion complete.")

        # Send video to Telegram
        send_telegram_video(mp4_path)
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        picam2.stop()
        picam2.close()

def send_telegram_video(video_path):
    """Sends the recorded video via Telegram Bot."""
    print(f"Sending video: {video_path}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, "rb") as video_file:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"video": video_file})
    
    if response.status_code == 200:
        print("✅ Video sent successfully.")
    else:
        print(f"❌ Failed to send video: {response.text}")
