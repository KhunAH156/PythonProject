import time
from threading import Thread
import queue
import app  # Import the Flask app module

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
#   from hal import hal_accelerometer as accel

from qrcode_scanner import scan_qr 

#Empty list to store sequence of keypad presses
shared_keypad_queue = queue.Queue()


# Authorized RFID tag
AUTHORIZED_RFID_TAG = 701707449650  # Set the correct RFID card

def run_flask_app():
    app.app.run(host="0.0.0.0", port=5000, use_reloader=False)

# Start Flask app in a separate thread
flask_thread = Thread(target=run_flask_app)
flask_thread.daemon = True
flask_thread.start()

#Call back function invoked when any key on keypad is pressed
def key_pressed(key):
    shared_keypad_queue.put(key)

#detecting user with ultrasonic
def detect_user():
    """Detect user presence using the ultrasonic sensor."""
    while True:
        distance = usonic.get_distance()  # Get the distance from the ultrasonic sensor
        if distance > 0 and distance < 50:  # Check if the user is within 50 cm
            return True  # User detected
        time.sleep(0.5)  # Check every 0.5 seconds

def wait_for_key():
    """Wait for a key press and return the key value."""
    return shared_keypad_queue.get()  # Block until a key is pressed

def handle_rfid_authorization(reader):
    """Handle payment authorization using an RFID card."""
    lcd = LCD.lcd()
    lcd.lcd_clear()
    lcd.lcd_display_string("Tap your card", 1)

    while True:
        rfid_id = reader.read_id_no_block()  # Get the RFID card ID
        if rfid_id:
            lcd.lcd_clear()
            if rfid_id == AUTHORIZED_RFID_TAG:
                lcd.lcd_display_string("Payment Accepted", 1)
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
        pot_value = adc.get_adc_value(1)  # Read potentiometer value
        if int(pot_value) >= 900:  # Door fully open (based on potentiometer value)
            servo.set_servo_position(90)  # Open the compartment
            lcd.lcd_clear()
            lcd.lcd_display_string("Door Opened", 1)
            time.sleep(1)
            break

    # Monitor IR sensor for hand removal and door close
    while True:
        ir_state = ir_sensor.get_ir_sensor_state()  # Detect hand presence
        if ir_state:  # If hand detected in the dispensing area
            lcd.lcd_clear()
            lcd.lcd_display_string("Remove hand", 1)
            buzzer.beep(0.5, 0.5, 2)
            time.sleep(2)
        else:
            pot_value = adc.get_adc_value(1)  # Read potentiometer value
        if int(pot_value) <= 200:  # Door Closed
            servo.set_servo_position(0)  #Closed
            lcd.lcd_clear()
            lcd.lcd_display_string("Thank You!", 1)
            time.sleep(1)
            break

def main():
    #initialization of HAL modules
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
    #accelerometer = accel.init()

    keypad.init(key_pressed)
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()

    lcd = LCD.lcd()
    lcd.lcd_clear()

    while True:
        # Detect user presence (REQ-1)
        user_present = detect_user()
        if user_present:
            # Log stock information for the owner

            # Display welcome message and main menu 
            lcd.lcd_clear()
            lcd.lcd_display_string("Hello", 1)
            time.sleep(2)
            lcd.lcd_clear()
            lcd.lcd_display_string("Welcome", 1)
            time.sleep(2)
            lcd.lcd_clear()
            lcd.lcd_display_string("1. Passcode", 1)
            lcd.lcd_display_string("2. QR Code", 2)
            time.sleep(2)  # Show the menu for a while before resetting

            # Wait for keypress
            key = wait_for_key()

            #buying physically
            if key == 1: 
                lcd.lcd_clear()
                lcd.lcd_display_string("Feature", 1)
                lcd.lcd_display_string("Unavailable", 2)
                '''
                # Handle RFID authorization
                if handle_rfid_authorization(reader):
                    # Unlock Door
                    unlocking_process()  # Call the dispensing process
                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Invalid Card", 1)
                    time.sleep(2)'''

            elif key == 2:
                # Handle QR Code (REQ-12)
                lcd.lcd_clear()
                lcd.lcd_display_string("Scanning QR Code", 1)
                time.sleep(2)

                # Run the QR scanning process
                key_validation = scan_qr()

                if key_validation:
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Access Granted", 1)
                    time.sleep(2) 
                    unlocking_process()  # Call the dispensing process
                    key_validation = None
                    
                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("QR Code Invalid", 1)
                    buzzer.beep(0.5, 0.5, 2)  # Buzzer for invalid input
                    time.sleep(2)
                    key_validation = None

            else:
                lcd.lcd_clear()
                lcd.lcd_display_string("Invalid Option", 1)
                buzzer.beep(0.2, 0.2, 3)  # Buzzer for invalid input
                time.sleep(2)

        lcd.lcd_clear()    

if __name__ == '__main__':
    main()