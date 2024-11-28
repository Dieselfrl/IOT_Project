#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>

//Define pins
#define SS_PIN 13
#define RST_PIN 33

MFRC522 rfid(SS_PIN, RST_PIN);  //Instance card reader RFID-RC522

const char* ssid = "";
const char* password = "";
const char* mqtt_server = "";
WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);                 //Instantiate serial interface
  setup_wifi();                         //Connecto to wifi
  client.setServer(mqtt_server, 1883);  //Instantiaite connection between ESP32 (client) and mqtt server
  SPI.begin(14, 25, 26, 13);            //Start comunication/SPI bus between master and slave
  rfid.PCD_Init();                      //Instantiate of card reader
}

//Connect to wifi
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

//Connect to MQTT server
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

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  char uidHex[20] = ""; 
  for (byte i = 0; i < rfid.uid.size; i++) {
    snprintf(uidHex + strlen(uidHex), sizeof(uidHex) - strlen(uidHex), "%02X", rfid.uid.uidByte[i]);
  }

  Serial.print("Publishing UID in Hexadecimal: ");
  Serial.println(uidHex);

  if (!client.publish("card/scanned", uidHex)) {
    Serial.println("Failed to publish UID.");
  }

  rfid.PICC_HaltA();
  delay(2000);
}
