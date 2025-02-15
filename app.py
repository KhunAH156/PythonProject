from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import mariadb
import qrcode
import os
import RPi.GPIO as GPIO
from time import sleep
from hal import hal_led as led
from hal import hal_temp_humidity_sensor as ths
from hal import hal_servo as servo

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong secret key

# Store last known sensor values
last_temperature = None
last_humidity = None


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
def home():
    if "logged_in" in session:
        return redirect(url_for("index"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Predefined login credentials (You can replace this with a database check)
        if username == "admin" and password == "password123":
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/index")
def index():
    if "logged_in" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/qrlist")
def qrlist():
    if "logged_in" not in session:
        return redirect(url_for("login"))
    return render_template("qrlist.html")

@app.route('/unlock', methods=['POST'])
def unlock():
    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    servo.set_servo_position(90)
    return jsonify({'status': 'Unlocked'})

@app.route('/lock', methods=['POST'])
def lock():
    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    servo.set_servo_position(0)
    return jsonify({'status': 'Locked'})

@app.route("/generate", methods=["POST"])
def generate():
    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403

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
        qr_url_path = f"/static/qrcodes/{key_id}.png"
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
    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT key_id FROM TemporaryQR")
        result = cursor.fetchall()
        qr_codes = [{"key_id": row[0]} for row in result]
        return jsonify(qr_codes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/led/on', methods=['POST'])
def led_on():
    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    led.set_output(24, True)  # Turn LED on
    return jsonify({'status': 'LED On'})

@app.route('/led/off', methods=['POST'])
def led_off():
    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403
    led.set_output(24, False)  # Turn LED off
    return jsonify({'status': 'LED Off'})

@app.route('/sensor', methods=['GET'])
def get_sensor_data():
    global last_temperature, last_humidity  # Use stored values

    if "logged_in" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    temp, humidity = ths.read_temp_humidity()

    if temp != -100 and humidity != -100:
        last_temperature = temp
        last_humidity = humidity

    # Return the last valid values if current reading fails
    return jsonify({
        "temperature": last_temperature if last_temperature is not None else "No Data",
        "humidity": last_humidity if last_humidity is not None else "No Data"
    })

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        servo.stop()
        GPIO.cleanup()