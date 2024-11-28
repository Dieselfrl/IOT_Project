#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>

// WiFi credentials
const char* ssid = "Yuan";
const char* password = "Maymaysa123";

// MQTT broker details
const char* mqtt_server = "192.168.171.150";
WiFiClient espClient;
PubSubClient client(espClient);

// Define pins for RFID
#define SS_PIN 13
#define RST_PIN 33

MFRC522 rfid(SS_PIN, RST_PIN);  // Instance card reader RFID-RC522

// Pin setup for photoresistor and LED
const int photoresistorPin = 32; // Photoresistor pin for light intensity measurement
const int ledPin = 27;           // LED pin to indicate light status

int lightLevel;

void setup() {
  Serial.begin(115200);                 // Instantiate serial interface

  // Setup WiFi
  setup_wifi();

  // Setup MQTT client
  client.setServer(mqtt_server, 1883);

  // Initialize SPI and RFID reader
  SPI.begin(14, 25, 26, SS_PIN);
  rfid.PCD_Init();

  // Pin modes for photoresistor and LED
  pinMode(photoresistorPin, INPUT);
  pinMode(ledPin, OUTPUT);
}

void setup_wifi() {
  // Connect to WiFi
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// Publish light level to MQTT broker
void lightLevelTrigger() {
  lightLevel = analogRead(photoresistorPin);
  Serial.print("Light level: ");
  Serial.println(lightLevel);

  char message[50];
  snprintf(message, 50, "%d", lightLevel);
  client.publish("light/data", message);

  // Control the LED based on the light intensity value
  if (lightLevel < 400) {
    digitalWrite(ledPin, HIGH); // Turn LED ON if intensity is low
  } else {
    digitalWrite(ledPin, LOW);  // Turn LED OFF if intensity is sufficient
  }

  delay(1000); // Wait 1 second before the next reading
}

// Reconnect to MQTT broker if disconnected
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000); // Retry every 5 seconds
    }
  }
}

void loop() {
  // Ensure MQTT connection is established
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Measure light intensity and trigger light level publishing
  lightLevelTrigger();

  // Handle RFID scanning
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Read and publish the UID of the scanned card
  char uidHex[20] = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    snprintf(uidHex + strlen(uidHex), sizeof(uidHex) - strlen(uidHex), "%02X", rfid.uid.uidByte[i]);
  }

  Serial.print("Publishing UID in Hexadecimal: ");
  Serial.println(uidHex);

  if (!client.publish("card/scanned", uidHex)) {
    Serial.println("Failed to publish UID.");
  }

  rfid.PICC_HaltA(); // Halt communication with the card

  delay(2000); // Wait 2 seconds before reading again
}
