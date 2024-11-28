import paho.mqtt.client as mqtt
from threading import Thread, Lock
import sqlite3
 
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

#Mqtt callback method (handle UID)
def on_message(client, userdata, message):
    uid = message.payload.decode()
    print(uid)
    user = getUserByUID(uid)
    if user is None:
        #take presets and set the global varriables
        insert_user(uid,400,400)
        print(f"User {uid} was created")
        user = getUserByUID(uid)
        
    global LIGHT_INTENSITY, TEMPERATURE_INTENSITY
    LIGHT_INTENSITY = user[2]
    TEMPERATURE_INTENSITY = user[3]
    print(f"Light intensity set to: {LIGHT_INTENSITY} | Temperature intensity set to: {TEMPERATURE_INTENSITY}")

#Instanciate mqtt connection
def mqtt_thread(): 
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60) #check what 1883 is there fore and the 60
    client.subscribe(MQTT_TOPIC)
    client.loop_forever()

mqtt_thread_instance = Thread(target=mqtt_thread)
mqtt_thread_instance.start()