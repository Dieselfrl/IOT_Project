from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import smtplib, ssl
import imaplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
import RPi.GPIO as GPIO
import time
import re
import logging
from Freenove_DHT import DHT

app = Flask(__name__)

# MQTT Configuration
MQTT_BROKER = "192.168.171.150"
MQTT_LIGHT_TOPIC = "light/data"
MQTT_RFID_TOPIC = "home/rfid"

# Global Variables
light_intensity = 0
led_status = "OFF"
email_sent = False
current_temperature = 0
current_humidity = 0
fan_status = False
rfid_user = "Unknown"

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
    global light_intensity, led_status, email_sent, rfid_user
    topic = message.topic
    payload = message.payload.decode()

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
    elif topic == MQTT_RFID_TOPIC:
        rfid_user = payload
        logger.info(f"RFID User: {rfid_user}")

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe([(MQTT_LIGHT_TOPIC, 0), (MQTT_RFID_TOPIC, 0)])
client.loop_start()

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

def check_for_response():
    logger.info("Checking for response in the inbox...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, EMAIL_PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, 'ALL')
    mail_ids = messages[0].split()

    for i in reversed(mail_ids[-10:]):  # Only check the last 10 emails for efficiency
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

# Fan Control
def control_fan(turn_on):
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

# Monitor Temperature
def monitor_temperature():
    global current_temperature, current_humidity
    alert_sent = False

    while True:
        chk = dht.readDHT11()
        if chk == 0:
            current_temperature = dht.getTemperature()
            current_humidity = dht.getHumidity()
            logger.info(f"Temperature: {current_temperature}°C, Humidity: {current_humidity}%")

            if current_temperature > TEMP_THRESHOLD:
                if not alert_sent or (not fan_status and not check_for_response()):
                    send_email("Temperature Alert", f"The current temperature is {current_temperature}°C. Would you like to turn on the fan? Reply YES or NO.")
                    alert_sent = True
                    logger.info("Temperature email sent. Waiting for user response...")

                if check_for_response():
                    logger.info("User responded 'YES'. Turning on the fan.")
                    control_fan(True)
                    alert_sent = False
                else:
                    logger.info("User did not respond 'YES' or fan remains OFF. Re-sending email in 10 seconds.")
                    time.sleep(10)
            else:
                alert_sent = False
                control_fan(False)
        time.sleep(2)

# Flask Routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/data')
def data():
    return jsonify({
        "lightIntensity": light_intensity,
        "ledStatus": led_status,
        "temperature": current_temperature,
        "humidity": current_humidity,
        "fanStatus": fan_status,
        "rfidUser": rfid_user
    })

@app.route('/control_fan', methods=['POST'])
def control_fan_route():
    data = request.get_json()
    if 'turnOn' in data:
        control_fan(data['turnOn'])
        return jsonify({"message": "Fan control updated"}), 200
    return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    try:
        threading.Thread(target=monitor_temperature).start()
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        GPIO.cleanup()
