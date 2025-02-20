import time
from threading import Thread
import queue
import app
import camera  # Import the Flask app module

from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_adc as adc
from hal import hal_buzzer as buzzer
from hal import hal_keypad as keypad
from hal import hal_moisture_sensor as moisture_sensor
from hal import hal_input_switch as input_switch
from hal import hal_ir_sensor as ir_sensor
from hal import hal_rfid_reader as rfid_reader
from hal import hal_servo as servo
from hal import hal_temp_humidity_sensor as temp_humid_sensor
from hal import hal_usonic as usonic
from hal import hal_dc_motor as dc_motor
from telegram import Bot
import db_setup as db

BOT_TOKEN = "7723998968:AAFc4QK-qRaIxCfqeqLYRs1OLuF-2z_OOiM"
CHAT_ID = "5819192033"

# Initialize Telegram Bot
bot = Bot(token=BOT_TOKEN)

message_sent = False

# Empty queue to store keypad input
shared_keypad_queue = queue.Queue()

# Authorized RFID tag
AUTHORIZED_RFID_TAG = 701707449650  # Set the correct RFID card

# Correct 4-digit passcode
CORRECT_PASSCODE = "1234"

def run_flask_app():
    app.app.run(host="0.0.0.0", port=5000, use_reloader=False)

# Start Flask app in a separate thread
flask_thread = Thread(target=run_flask_app)
flask_thread.daemon = True
flask_thread.start()

# Call back function invoked when any key on keypad is pressed
def key_pressed(key):
    shared_keypad_queue.put(key)

# Function to send Telegram message
def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Telegram message sent: {message}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# Detect user with ultrasonic sensor
def detect_user():
    """Detect user presence using the ultrasonic sensor."""
    while True:
        distance = usonic.get_distance()
        if 0 < distance < 50:
            return True
        time.sleep(0.5)

def wait_for_key():
    """Wait for a key press and return the key value."""
    return shared_keypad_queue.get()

def enter_passcode():
    """Handles masked passcode input from keypad"""
    lcd = LCD.lcd()
    lcd.lcd_clear()
    lcd.lcd_display_string("Enter Passcode:", 1)
    
    entered_code = ""
    
    while len(entered_code) < 4:
        key = None
        while key is None:
            key = wait_for_key()  # Wait for user input

        if key in range(10):  # If key is 0-9
            entered_code += str(key)
            masked_display = "*" * len(entered_code)  #Mask input
            lcd.lcd_display_string(masked_display, 2)
        
        elif key == "#":  # Enter key (optional)
            break

    return entered_code

def handle_rfid_authorization(reader):
    """Handle authorization using an RFID card."""
    lcd = LCD.lcd()
    lcd.lcd_display_string("Tap Card", 1)

    while True:
        rfid_id = reader.read_id_no_block()
        if rfid_id:
            lcd.lcd_clear()
            if rfid_id == AUTHORIZED_RFID_TAG:
                lcd.lcd_display_string("Card Accepted", 1)
                time.sleep(2)
                return True
            else:
                lcd.lcd_display_string("Invalid Card", 1)
                buzzer.beep(0.5, 0.5, 2)
                time.sleep(2)
                lcd.lcd_clear()


def unlocking_process():
    """Handle the door unlocking."""
    lcd = LCD.lcd()
    lcd.lcd_clear()
    lcd.lcd_display_string("Please turn knob", 1)
    lcd.lcd_display_string("to open door", 2)

    while True: 
        pot_value = adc.get_adc_value(1)
        if int(pot_value) >= 900:
            servo.set_servo_position(90)
            lcd.lcd_clear()
            lcd.lcd_display_string("Door Opened", 1)
            send_telegram_message("The door is opened")
            print("telegram")
            time.sleep(1)
            break

    while True:
        ir_state = ir_sensor.get_ir_sensor_state()
        if ir_state:
            lcd.lcd_clear()
            lcd.lcd_display_string("Remove hand", 1)
            buzzer.beep(0.5, 0.5, 2)
            time.sleep(2)
        else:
            pot_value = adc.get_adc_value(1)
        if int(pot_value) <= 200:
            servo.set_servo_position(0)
            lcd.lcd_clear()
            lcd.lcd_display_string("Thank You!", 1)
            send_telegram_message("The door is closed")
            time.sleep(1)
            break

def main():
    #Inintialize the database
    db.setup_database()
    
    # Initialization of HAL modules
    led.init()
    adc.init()
    buzzer.init()
    moisture_sensor.init()
    input_switch.init()
    ir_sensor.init()
    reader = rfid_reader.init()
    servo.init()
    temp_humid_sensor.init()
    usonic.init()
    dc_motor.init()

    keypad.init(key_pressed)
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()
    global failed_attempt
    failed_attempt = 0

    lcd = LCD.lcd()
    lcd.lcd_clear()

    while True:
        user_present = detect_user()
        if user_present:
            lcd.lcd_clear()
            lcd.lcd_display_string("Hello", 1)
            time.sleep(2)
            lcd.lcd_clear()
            lcd.lcd_display_string("Welcome", 1)
            time.sleep(2)
            lcd.lcd_clear()
            lcd.lcd_display_string("1. Passcode", 1)
            lcd.lcd_display_string("2. QR Code", 2)

            key = wait_for_key()

            # Passcode Login Feature
            if key == 1:
                lcd.lcd_clear()
                lcd.lcd_display_string("Passcode Login", 1)
                time.sleep(2)

                passcode = enter_passcode()

                if passcode == CORRECT_PASSCODE:
                    failed_attempt = 0  #Reset failed attempts on success
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Access Granted", 1)
                    time.sleep(2)
                    send_telegram_message("Access Granted")
                    unlocking_process()
                else:
                    failed_attempt += 1  #Increment failed attempts
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Access Denied", 1)
                    send_telegram_message("Access Denied")
                    buzzer.beep(0.5, 0.5, 2)
                    time.sleep(2)

                    # ✅ If failed attempts reach 5, send alert and reset counter
                    if failed_attempt >= 2:
                        lcd.lcd_clear()
                        lcd.lcd_display_string("Too Many Attempts!", 1)
                        send_telegram_message("WARNING: Too many failed login attempts!")

                        print("⚠️ Too many failed attempts. Recording video...")
                        camera.record_and_send_video()

                        time.sleep(3)
                        failed_attempt = 0


            # QR Code Login Feature
            elif key == 2:
                lcd.lcd_clear()
                lcd.lcd_display_string("Scanning QR Code", 1)
                time.sleep(2)

                key_validation = camera.scan_qr()

                if key_validation:
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Access Granted", 1)
                    time.sleep(2)
                    unlocking_process()
                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("QR Code Invalid", 1)
                    failed_attempt += 1
                    buzzer.beep(0.5, 0.5, 2)
                    time.sleep(2)

            elif key == 3:
                start_time = time.time()  # Start the 15-second session
                cardOk = False

                while time.time() - start_time < 15:  # Allow 15 seconds for tapping
                    cardOk = handle_rfid_authorization(reader)
                    if cardOk:
                        unlocking_process()
                        break  # Exit the loop if a valid card is detected

                if not cardOk:  # If time runs out without a valid card
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Error: Timeout", 1)

            
            else:
                lcd.lcd_clear()
                lcd.lcd_display_string("Invalid Option", 1)
                buzzer.beep(0.2, 0.2, 3)
                time.sleep(2)

        lcd.lcd_clear()

if __name__ == '__main__':
    main()
