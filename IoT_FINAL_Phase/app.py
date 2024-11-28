from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import sqlite3
import logging
import random
import RPi.GPIO as GPIO
import smtplib, ssl
import imaplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import re
from threading import Thread
from Freenove_DHT import DHT

app = Flask(__name__)

# MQTT Configuration
MQTT_BROKER = "192.168.171.150"
MQTT_LIGHT_TOPIC = "light/data"
MQTT_RFID_TOPIC = "home/rfid"

# Global Variables
rfid_user = "Unknown"
current_temperature = 0
light_intensity = 0
led_status = "OFF"
email_sent = False
current_humidity = 0
fan_status = False

# Pin setup
DHTPin = 17  # DHT11 sensor pin
Motor1, Motor2, Motor3 = 22, 27, 17  # Motor control pins
LED_PIN = 5  # LED control pin
TEMP_THRESHOLD = 24  # Temperature threshold

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(Motor1, GPIO.OUT)
GPIO.setup(Motor2, GPIO.OUT)
GPIO.setup(Motor3, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

dht = DHT(DHTPin)

# Email Configuration
EMAIL = 'stevenbeaven234@gmail.com'
EMAIL_PASSWORD = 'bfic leud wpdi xkki'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
IMAP_SERVER = 'imap.gmail.com'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT Client Setup
def on_message(client, userdata, message):
    global rfid_user, current_temperature, light_intensity, led_status, email_sent
    topic = message.topic
    payload = message.payload.decode()

    if topic == MQTT_RFID_TOPIC:
        rfid_user = payload
        register_user_with_thresholds(rfid_user)
        rfid_user = get_user_by_rfid(rfid_user)
        logger.info(f"RFID User: {rfid_user}")

    if topic == MQTT_LIGHT_TOPIC:
        light_intensity = int(payload)
        if light_intensity < 400:
            led_status = "ON"
            GPIO.output(LED_PIN, GPIO.HIGH)
            if not email_sent:
                send_email("Light Notification", f"The Light is ON at {time.strftime('%H:%M')}.")
        else:
            led_status = "OFF"
            GPIO.output(LED_PIN, GPIO.LOW)
            email_sent = False

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe([(MQTT_LIGHT_TOPIC, 0), (MQTT_RFID_TOPIC, 0)])
client.loop_start()

# Database Integration
def get_user_by_rfid(rfid_tag):
    try:
        conn = sqlite3.connect('rfid_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE rfid_tag = ?', (rfid_tag,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "Unknown"
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        return "Unknown"

def register_user_with_thresholds(rfid_tag):
    try:
        conn = sqlite3.connect('rfid_users.db')
        cursor = conn.cursor()

        # Generate random thresholds within a reasonable range
        temp_threshold = random.uniform(22.0, 28.0)  # Temperature threshold between 22°C and 28°C
        light_threshold = random.randint(300, 700)    # Light intensity threshold between 300 and 700
        humidity_threshold = random.uniform(40.0, 60.0)  # Humidity threshold between 40% and 60%

        # Insert or update user in the database
        cursor.execute('''
            INSERT INTO users (rfid_tag, temp_threshold, light_threshold, humidity_threshold)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(rfid_tag) DO UPDATE SET
                temp_threshold=excluded.temp_threshold,
                light_threshold=excluded.light_threshold,
                humidity_threshold=excluded.humidity_threshold
        ''', (rfid_tag, temp_threshold, light_threshold, humidity_threshold))

        conn.commit()
        conn.close()
        logger.info(f"User with RFID {rfid_tag} registered/updated with thresholds: Temp={temp_threshold}, Light={light_threshold}, Humidity={humidity_threshold}")
    except Exception as e:
        logger.error(f"Error registering user with thresholds: {e}")

# Email Functions
def send_email(subject, body):
    global email_sent
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        email_sent = True
        logger.info(f"{subject} email sent")
    except Exception as e:
        logger.error(f"Failed to send {subject} email: %s", e)
    finally:
        server.quit()

# Flask Routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/data')
def data():
    return jsonify({
        "rfidUser": rfid_user,
        "temperature": current_temperature,
        "lightIntensity": light_intensity,
        "ledStatus": led_status,
        "fanStatus": fan_status
    })

if __name__ == '__main__':
    try:
        Thread(target=client.loop_forever).start()
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        GPIO.cleanup()
