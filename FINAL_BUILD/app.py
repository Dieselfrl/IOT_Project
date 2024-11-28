from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from threading import Thread, Lock
import smtplib, ssl
import imaplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import sqlite3
import time
from Freenove_DHT import DHT

app = Flask(__name__)
thread_lock = Lock()

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS User (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    UID TEXT UNIQUE NOT NULL,
    light_intensity INTEGER,
    temperature_intensity INTEGER
)
""")

#Mqtt server information
MQTT_BROKER = ""
MQTT_TOPIC = "card/scanned"

#global varriables/user presets
LIGHT_INTENSITY = 0
TEMPERATURE_INTENSITY = 0

#DHT SETUP + MOTOR
DHTPin = 17
current_temperature = 0
current_humidity = 0
fan_status = False
Motor1, Motor2, Motor3 = 22, 27, 17  

isLogged = False
led_status = "OFF"
email_sent = False

#LED settings
LED_PIN = 18
light_intensity = 0
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

EMAIL = 'stevenbeaven234@gmail.com'
EMAIL_PASSWORD = 'bfic leud wpdi xkki'
RECIPIENT_EMAIL = "stevenbeaven234@gmail.com"
IMAP_SERVER = "imap.gmail.com"

rfidUser = ""

temperature_thread = None
is_monitoring = False

#Get user by UID
def getUserByUID(uid):
    with thread_lock:
        try:
            cursor.execute(
                "SELECT * FROM User WHERE UID = ?",
                (uid,)
            )
            user = cursor.fetchone()
            print("User was found!")
            return user
        except sqlite3.Error as e:
            print(f"User was not found! Error: {e}")
        return None
    
#Inserting user    
def insert_user(uid, light_intensity, temperature_intensity):
    with thread_lock:  # Synchronize access
        try:
            cursor.execute(
                "INSERT INTO User (UID, light_intensity, temperature_intensity) VALUES (?, ?, ?)",
                (uid, light_intensity, temperature_intensity)
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error while inserting user {uid}: {e}")

def send_email(body):
    global email_sent
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = "Light Notification"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        email_sent = True
        print("Email sent")
    except Exception as e:
        print("Failed to send email:", e)
    finally:
        server.quit()

#check for email response
def check_for_response():
    try:
        print("Checking for response in the inbox...")
        with imaplib.IMAP4_SSL(IMAP_SERVER) as mail:
            mail.login(EMAIL, EMAIL_PASSWORD)
            mail.select("inbox")
            status, messages = mail.search(None, 'ALL')
            mail_ids = messages[0].split()
            for i in reversed(mail_ids[-10:]):  # Only check the last 10 emails
                status, msg_data = mail.fetch(i, '(RFC822)')
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        print("Email received from:", msg['From'])
                        print("Email subject:", msg['Subject'])
                        subject = msg['Subject'] or ""
                        if re.search(r"\bTemperature Alert\b", subject, re.IGNORECASE):
                            content = ""
                            if msg.is_multipart():
                                for payload in msg.get_payload():
                                    if payload.get_content_type() == 'text/plain':
                                        content = payload.get_payload(decode=True).decode().strip()
                            else:
                                content = msg.get_payload(decode=True).decode().strip()
                            print("Full email body read:", content)
                            first_line = content.splitlines()[0].strip().upper()
                            return first_line == "YES"
        print("No relevant response found in inbox.")
        return False
    except Exception as e:
        print(f"Error checking for email response: {e}")
        return False

#Motor control
def control_fan(turn_on):
    global fan_status
    if turn_on:
        GPIO.output(Motor1, GPIO.HIGH)
        GPIO.output(Motor2, GPIO.LOW)
        GPIO.output(Motor3, GPIO.HIGH)
        fan_status = True
        print("Fan is ON.")
    else:
        GPIO.output(Motor1, GPIO.LOW)
        GPIO.output(Motor2, GPIO.LOW)
        GPIO.output(Motor3, GPIO.LOW)
        fan_status = False
        print("Fan is OFF.")

#runtime loop method for dht11
def monitor_temperature():
    global current_temperature, current_humidity
    alert_sent = False
    while True:
        try:
            chk = dht.readDHT11()
            if chk == 0:
                current_temperature = dht.getTemperature()
                current_humidity = dht.getHumidity()
                print(f"Temperature: {current_temperature}°C, Humidity: {current_humidity}%")
                if current_temperature > TEMPERATURE_INTENSITY:
                    if not alert_sent:
                        send_email("Temperature Alert", f"The current temperature is {current_temperature}°C. Would you like to turn on the fan? Reply YES or NO.")
                        alert_sent = True
                        print("Temperature email sent. Waiting for user response...")
                    if check_for_response():
                        print("User responded 'YES'. Turning on the fan.")
                        control_fan(True)
                        alert_sent = False  # Reset alert flag
                    else:
                        print("No valid response. Re-checking in 10 seconds.")
                        time.sleep(10)
                else:
                    alert_sent = False
                    control_fan(False)
            time.sleep(2)
        except Exception as e:
            print(f"Error in monitor_temperature: {e}")


#Mqtt callback method (handle UID)
def on_message(client, userdata, message):
    
    #Verify topic
    if message.topic == MQTT_TOPIC:
        uid = message.payload.decode()
        print(uid)
        user = getUserByUID(uid)
        if user is None:
            #take presets and set the global varriables
            insert_user(uid,400,400)
            print(f"User {uid} was created")
            user = getUserByUID(uid)
        
        global LIGHT_INTENSITY, TEMPERATURE_INTENSITY, isLogged, light_intensity
        isLogged = True
        LIGHT_INTENSITY = user[2]
        TEMPERATURE_INTENSITY = user[3]
        print(f"Light intensity set to: {LIGHT_INTENSITY} | Temperature intensity set to: {TEMPERATURE_INTENSITY}")
        rfidUser = uid
        body = f"{uid} has signed in at {time.strftime('%H:%M')}."
        send_email(body)
    elif message.topic == "room/light":
        #Verify if a user was logged in
        if isLogged:
            #start checking dht11
            if not is_monitoring:
                is_monitoring = True
                temperature = Thread(targer=monitor_temperature)
                temperature.start()
                print("Temperature monitoring started.")
                
            global email_sent, led_status
            light_intensity = int(message.payload.decode())
            if light_intensity < LIGHT_INTENSITY:
                GPIO.output(LED_PIN, GPIO.HIGH)
                if not email_sent:
                    body = f"The Light is ON at {time.strftime('%H:%M')}."
                    send_email(body)
            else:
                GPIO.output(LED_PIN, GPIO.LOW)
                email_sent = False
            
        

#Instanciate mqtt connection
def mqtt_thread(): 
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60) #check what 1883 is there fore and the 60
    client.subscribe(MQTT_TOPIC)
    client.subscribe("room/light")
    client.loop_forever()

mqtt_thread_instance = Thread(target=mqtt_thread)
mqtt_thread_instance.start()

@app.route('/')
def index():
    return "Welcome to IOT PROJECT!"

@app.route('/data')
def data():
    print(f"Temperature: {current_temperature}")
    print(f"Light Intensity: {light_intensity}")
    print(f"LED Status: {led_status}")
    print(f"Humidity: {current_humidity}")
    print(f"Fan Status: {fan_status}")
    print(f"RFID User: {rfidUser}")

    return jsonify({
        "temperature": current_temperature,
        "lightIntensity": light_intensity,
        "ledStatus": led_status,
        "humidity": current_humidity,
        "fanStatus": fan_status,
        "rfidUser": rfidUser
    })

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("Shutting down...")