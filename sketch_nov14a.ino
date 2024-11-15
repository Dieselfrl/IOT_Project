#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP_Mail_Client.h>

const char* ssid = "";
const char* password = "";
const char* mqtt_server = "";
WiFiClient espClient;
PubSubClient client(espClient);

SMTPSession smtp;
Session_Config config;

const int smtp_port = 465;
const char* email_sender_account = "stevenbeaven234@gmail.com";
const char* email_sender_password = "flhw tgbz azst obiv";
const char* email_recipient = "cristian.andrei.gasper@gmail.com";

const int ledPin = 27;
const int photoPin = 32;
int lightLevel;
bool isLedOn = false;

//Seting up esp 32
void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  pinMode(ledPin, OUTPUT);

  config.server.host_name = "smtp.gmail.com";
  config.server.port = 587;
  config.login.email = email_sender_account;
  config.login.password = email_sender_password;
}

//Connectiing to wifi
void setup_wifi() {
  delay(10);

  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void sendEmail(String subject, String messageText) {
  SMTP_Message message;
  message.sender.name = "ESP32";
  message.sender.email = email_sender_account;
  message.subject = subject;
  message.addRecipient("Recipient", email_recipient);
  message.text.content = messageText;

  smtp.callback(smtpCallback);
  smtp.connect(&config);

  if (!MailClient.sendMail(&smtp, &message)) {
    Serial.println("Error sending email: " + smtp.errorReason());
  } else {
    Serial.println("Email sent successfully!");
  }
  message.clear();
}

void smtpCallback(SMTP_Status status) {
  Serial.println(status.info());
}
//Message handling
void callback(String topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messagein;

  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messagein += (char)message[i];
  }
  if (topic == "room/light") {
    if (messagein == "ON" && !isLedOn) {
      Serial.println("Light is ON");
      digitalWrite(ledPin, HIGH);
      isLedOn = true;
      sendEmail("Alert: Light is ON", "The light level is below threshold, and the light is ON.");
    } else if (messagein != "ON" && isLedOn) {
      Serial.println("Light is OFF");
      digitalWrite(ledPin, LOW);
      isLedOn = false;
      sendEmail("Alert: Light is OFF", "The light level has gone above threshold, and the light is OFF.");
    }
  }
}

//MQTT connection
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("vanieriot")) {
      Serial.println("connected");
      client.subscribe("room/light");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void lightLevelTrigger() {
  lightLevel = analogRead(photoPin);
  Serial.print("Light level: ");
  Serial.println(lightLevel);

  if (lightLevel < 400) {
    client.publish("room/light", "ON");
  } else {
    client.publish("room/light", "OFF");
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  lightLevelTrigger();
  delay(5000);
}