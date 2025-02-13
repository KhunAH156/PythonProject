from flask import Flask, request, jsonify, render_template
import mariadb
import qrcode
import os
import RPi.GPIO as GPIO
from time import sleep

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(26, GPIO.OUT)
servo = GPIO.PWM(26, 50)  # 50Hz PWM
servo.start(0)

def set_servo_position(position):
    duty_cycle = (-10 * position) / 180 + 12
    print(f"Setting servo to position {position} (duty cycle: {duty_cycle})")
    servo.ChangeDutyCycle(duty_cycle)
    sleep(0.5)
    servo.ChangeDutyCycle(0)  # Stop sending signal to avoid jitter

def get_db_connection():
    try:
        connection = mariadb.connect(
            host="localhost",
            user="root",
            password="",
            database="smart_door_lock"
        )
        return connection
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/qrlist")
def qrlist():
    return render_template("qrlist.html")

@app.route('/unlock', methods=['POST'])
def unlock():
    set_servo_position(0)  # Adjust according to servo's angle
    return jsonify({'status': 'Unlocked'})

@app.route('/lock', methods=['POST'])
def lock():
    set_servo_position(180)  # Adjust according to servo's angle
    return jsonify({'status': 'Locked'})

@app.route("/generate", methods=["POST"])
def generate():
    key_id = os.urandom(8).hex()  # Generate random key ID

    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO TemporaryQR (key_id) VALUES (?)", (key_id,))
        connection.commit()
        print(f"Inserted key_id: {key_id}")

        # Generate QR Code
        qr = qrcode.make(key_id)
        qr_path = f"static/qrcodes/{key_id}.png"
        qr_url_path = f"/static/qrcodes/{key_id}.png"  # Correct URL path for client access
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        qr.save(qr_path)
        print(f"QR Code saved at: {qr_path}")

        return jsonify({"key_id": key_id, "qr_code_path": qr_url_path}), 201

    except mariadb.Error as err:
        print(f"Database error: {err}")
        return jsonify({"error": "Database error: " + str(err)}), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "Unexpected error: " + str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@app.route("/qrlist1")
def qrlist1():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT key_id FROM TemporaryQR")
        result = cursor.fetchall()
        qr_codes = [{"key_id": row[0]} for row in result]
        return jsonify(qr_codes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        servo.stop()
        GPIO.cleanup()
