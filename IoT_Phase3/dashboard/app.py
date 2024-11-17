from flask import Flask, render_template
import paho.mqtt.client as mqtt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
import time

app = Flask(__name__)

# MQTT Configuration
MQTT_BROKER = "put mqtt server ip"
MQTT_TOPIC = "light/data"

# Global Variables
light_intensity = 0
led_status = "OFF"
email_sent = False

# Email Configuration
EMAIL = 'stevenbeaven234@gmail.com'
EMAIL_PASSWORD = 'bfic leud wpdi xkki'
RECIPIENT_EMAIL = "stevenbeaven234@gmail.com"

def send_email():
    global email_sent
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = "Light Notification"
    body = f"The Light is ON at {time.strftime('%H:%M')}."
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


def on_message(client, userdata, message):
    global light_intensity, led_status, email_sent
    light_intensity = int(message.payload.decode())
    if light_intensity < 400:
        led_status = "ON"
        if not email_sent:
            send_email()
    else:
        led_status = "OFF"
        email_sent = False

def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_forever()


mqtt_thread_instance = Thread(target=mqtt_thread)
mqtt_thread_instance.daemon = True
mqtt_thread_instance.start()


@app.route('/')
def dashboard():

    return render_template('light_sensor.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')