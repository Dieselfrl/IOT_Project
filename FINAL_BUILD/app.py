import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from threading import Thread, Lock
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import time

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
isLogged = False
led_status = "OFF"
email_sent = False

#LED settings
LED_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

EMAIL = 'stevenbeaven234@gmail.com'
EMAIL_PASSWORD = 'bfic leud wpdi xkki'
RECIPIENT_EMAIL = "stevenbeaven234@gmail.com"

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

#Mqtt callback method (handle UID)
def on_message(client, userdata, message):
    
    #Verify topic
    if message.topic == MQTT_TOPIC:
        uid = message.payload.decode()
        print(uid)
        user = getUserByUID(uid)
        body = ""
        if user is None:
            #take presets and set the global varriables
            insert_user(uid,400,400)
            print(f"User {uid} was created")
            user = getUserByUID(uid)
            body = f"{uid} has created account {time.strftime('%H:%M')}. "
        
        global LIGHT_INTENSITY, TEMPERATURE_INTENSITY, isLogged
        isLogged = True
        LIGHT_INTENSITY = user[2]
        TEMPERATURE_INTENSITY = user[3]
        print(f"Light intensity set to: {LIGHT_INTENSITY} | Temperature intensity set to: {TEMPERATURE_INTENSITY}")
        body = f"{uid} has signed in at {time.strftime('%H:%M')}."
        send_email(body)
    elif message.topic == "room/light":
        #Verify if a user was logged in
        if isLogged:
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