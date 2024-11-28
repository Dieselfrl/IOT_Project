import time
import RPi.GPIO as GPIO
from Freenove_DHT import DHT
import smtplib, ssl
import imaplib, email
from email.mime.text import MIMEText
from flask import Flask, render_template, jsonify
import threading
import logging
import re
import paho.mqtt.client as mqtt
import sqlite3
from threading import Lock

# Pin setup
DHTPin = 17  # DHT11 sensor pin
Motor1, Motor2, Motor3 = 16, 20, 21  # Motor control pins

# Email setup
EMAIL = 'stevenbeaven234@gmail.com'
PASSWORD = 'meux rraz btsw jzfw'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
IMAP_SERVER = 'imap.gmail.com'
TEMP_THRESHOLD = 10  # Temperature threshold

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(Motor1, GPIO.OUT)
GPIO.setup(Motor2, GPIO.OUT)
GPIO.setup(Motor3, GPIO.OUT)

# Flask app for the dashboard
app = Flask(__name__, static_folder='static')
current_temperature = 0
current_humidity = 0
fan_status = False  # Track fan status

# MQTT Configuration
MQTT_BROKER = "192.168.171.150"
MQTT_TOPIC_LIGHT = "light/data"
MQTT_TOPIC_CARD = "card/scanned"
light_intensity = 0
led_status = "OFF"
email_sent = False

# SQLite setup
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
thread_lock = Lock()

cursor.execute("""
CREATE TABLE IF NOT EXISTS User (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    UID TEXT UNIQUE NOT NULL,
    light_intensity INTEGER,
    temperature_intensity INTEGER
)
""")
conn.commit()

# Global variables for user presets
LIGHT_INTENSITY = 0
TEMPERATURE_INTENSITY = 0

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email Functions
def send_email(temp):
    """Send email alert if the temperature exceeds the threshold."""
    context = ssl.create_default_context()
    message = MIMEText(f"The current temperature is {temp}°C. Would you like to turn on the fan? Reply YES or NO.")
    message['Subject'] = 'Temperature Alert'
    message['From'] = EMAIL
    message['To'] = EMAIL

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(context=context)
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, EMAIL, message.as_string())
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error("Error sending email: %s", e)
    finally:
        server.quit()

def check_for_response():
    """Check for user response to the temperature alert email."""
    logger.info("Checking for response in the inbox...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, 'ALL')
    mail_ids = messages[0].split()

    for i in reversed(mail_ids):
        status, msg_data = mail.fetch(i, '(RFC822)')
        for part in msg_data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                logger.info("Email received from: %s", msg['From'])
                logger.info("Email subject: %s", msg['Subject'])

                subject = msg['Subject'] or ""
                if re.search(r"\bTemperature Alert\b", subject, re.IGNORECASE):
                    content = ""
                    if msg.is_multipart():
                        for payload in msg.get_payload():
                            if payload.get_content_type() == 'text/plain':
                                content = payload.get_payload(decode=True).decode().strip()
                    else:
                        content = msg.get_payload(decode=True).decode().strip()

                    logger.info("Full email body read: %s", content)
                    first_line = content.splitlines()[0].strip().upper()

                    if first_line == "YES":
                        return True
                    else:
                        logger.info("Received response, but not 'YES'. Fan remains OFF.")
                        return False
    logger.info("No relevant response found in inbox.")
    return False

# SQLite Functions
def get_user_by_uid(uid):
    with thread_lock:
        try:
            cursor.execute(
                "SELECT * FROM User WHERE UID = ?",
                (uid,)
            )
            user = cursor.fetchone()
            if user:
                print("User was found!")
            return user
        except sqlite3.Error as e:
            print(f"User was not found! Error: {e}")
        return None

def insert_user(uid, light_intensity, temperature_intensity):
    with thread_lock:
        try:
            cursor.execute(
                "INSERT INTO User (UID, light_intensity, temperature_intensity) VALUES (?, ?, ?)",
                (uid, light_intensity, temperature_intensity)
            )
            conn.commit()
            print(f"User {uid} was created")
        except sqlite3.Error as e:
            print(f"Error while inserting user {uid}: {e}")

# MQTT Functions
def on_message(client, userdata, message):
    global light_intensity, led_status, email_sent, LIGHT_INTENSITY, TEMPERATURE_INTENSITY
    topic = message.topic
    if topic == MQTT_TOPIC_LIGHT:
        light_intensity = int(message.payload.decode())
        if light_intensity < 400:
            led_status = "ON"
            if not email_sent:
                send_email(current_temperature)
                email_sent = True
        else:
            led_status = "OFF"
            email_sent = False
    elif topic == MQTT_TOPIC_CARD:
        uid = message.payload.decode()
        print(f"Card scanned with UID: {uid}")
        user = get_user_by_uid(uid)
        if user is None:
            insert_user(uid, 400, 400)
            user = get_user_by_uid(uid)

        LIGHT_INTENSITY = user[2]
        TEMPERATURE_INTENSITY = user[3]
        print(f"Light intensity set to: {LIGHT_INTENSITY} | Temperature intensity set to: {TEMPERATURE_INTENSITY}")

def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC_LIGHT)
    client.subscribe(MQTT_TOPIC_CARD)
    client.loop_forever()

def control_fan(turn_on):
    """Control the motor (fan) based on the user's response."""
    global fan_status
    if turn_on:
        GPIO.output(Motor1, GPIO.HIGH)
        GPIO.output(Motor2, GPIO.LOW)
        GPIO.output(Motor3, GPIO.HIGH)
        fan_status = True
        logger.info("Fan is ON.")
    else:
        GPIO.output(Motor1, GPIO.LOW)
        GPIO.output(Motor2, GPIO.LOW)
        GPIO.output(Motor3, GPIO.LOW)
        fan_status = False
        logger.info("Fan is OFF.")

def monitor_temperature():
    """Continuously monitor temperature and control fan based on user response."""
    global current_temperature, current_humidity
    dht = DHT(DHTPin)
    alert_sent = False

    while True:
        chk = dht.readDHT11()
        if chk == 0:
            current_temperature = dht.getTemperature()
            current_humidity = dht.getHumidity()
            logger.info(f"Temperature: {current_temperature}°C, Humidity: {current_humidity}%")

            if current_temperature > TEMP_THRESHOLD:
                if not alert_sent or (not fan_status and not check_for_response()):
                    send_email(current_temperature)
                    alert_sent = True
                    logger.info("Email sent. Waiting for user response...")

                if check_for_response():
                    logger.info("User responded 'YES'. Turning on the fan.")
                    control_fan(True)
                    alert_sent = False  # Reset alert status if the fan is turned on
                else:
                    logger.info("User did not respond 'YES' or fan remains OFF. Re-sending email in 10 seconds.")
                    time.sleep(10)  # Wait 10 seconds before re-sending the alert
            else:
                alert_sent = False
                control_fan(False)  # Turn off the fan if temperature is below the threshold
        time.sleep(2)

mqtt_thread_instance = threading.Thread(target=mqtt_thread)
mqtt_thread_instance.daemon = True
mqtt_thread_instance.start()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/data')
def data():
    """Provide current sensor data to the dashboard."""
    return jsonify(
        temperature=current_temperature,
        humidity=current_humidity,
        fan_status=fan_status,
        lightIntensity=light_intensity,
        ledStatus=led_status,
        emailSent=email_sent
    )

if __name__ == '__main__':
    try:
        # Run Flask server in the main thread for visibility in terminal output
        threading.Thread(target=monitor_temperature).start()
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        GPIO.cleanup()
