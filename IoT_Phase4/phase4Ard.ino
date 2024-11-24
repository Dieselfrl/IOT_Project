#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>


// Define pins for RFID
#define SS_PIN 5 // SDA Pin on RC522
#define RST_PIN 4 // RST Pin on RC522

MFRC522 rfid(SS_PIN, RST_PIN); // Create MFRC522 instance
const char* ssid = "Crackers";
const char* password = "ChrisDuck";
const char* mqtt_server = "192.168.167.214";
WiFiClient espClient;
PubSubClient client(espClient);


const char* topic = "light/data";


const int photoresistorPin = 32; 
const int tempresistorPin = 30; 
const int ledPin = 27;

void setup() {
  pinMode(photoresistorPin, INPUT);
  pinMode(tempresistorPin, INPUT);
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  SPI.begin(); // Initialize SPI bus
rfid.PCD_Init(); // Initialize MFRC522 reader
Serial.println("Place your RFID card near the reader...");
}


void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}


void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  int tempIntensity = analogRead(tempresistorPin);
  Serial.print("Temperature Intensity: ");
  Serial.println(tempIntensity);

  int lightIntensity = analogRead(photoresistorPin);
  Serial.print("Light Intensity: ");
  Serial.println(lightIntensity);

  char message[50];
  snprintf(message, 50, "%d", lightIntensity);
  client.publish(topic, message);

   char message[50];
  snprintf(message, 50, "%d", tempIntensity);
  client.publish(topic, message);
  
  if(lightIntensity<400){
  digitalWrite(ledPin,HIGH);
  }else{
  digitalWrite(ledPin,LOW);
  }
  
  // Look for new cards
if (!rfid.PICC_IsNewCardPresent()) {
return;
}
Note: Install the MFRC522.h library which allows dialogue with the module.
// Select one of the cards
if (!rfid.PICC_ReadCardSerial()) {
return;
}
// Print UID
Serial.print("Card UID:");
for (byte i = 0; i < rfid.uid.size; i++) {
Serial.print(rfid.uid.uidByte[i] < 0x10 ? " 0" : " ");
Serial.print(rfid.uid.uidByte[i], HEX);
}
Serial.println();
// Halt PICC
rfid.PICC_HaltA();

  delay(2000);


}


void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      delay(5000);
    }
  }
}