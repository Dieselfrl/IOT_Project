#include <WiFi.h>
#include <PubSubClient.h>

// WiFi credentials
const char* ssid = "Yuan";
const char* password = "Maymaysa123";

// MQTT broker details
const char* mqtt_server = "192.168.171.150";
WiFiClient espClient;
PubSubClient client(espClient);

const char* topic = "light/data";

// Pin setup
const int photoresistorPin = 32; // Photoresistor pin for light intensity measurement
const int ledPin = 27; // LED pin to indicate light status

void setup() {
  pinMode(photoresistorPin, INPUT);
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void setup_wifi() {
  // Connect to WiFi
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

  // Read the light intensity from the photoresistor
  int lightIntensity = analogRead(photoresistorPin);
  Serial.print("Light Intensity: ");
  Serial.println(lightIntensity);

  // Publish the light intensity value to the MQTT broker
  char message[50];
  snprintf(message, 50, "%d", lightIntensity);
  client.publish(topic, message);

  // Control the LED based on the light intensity value
  if (lightIntensity < 400) {
    digitalWrite(ledPin, HIGH); // Turn LED ON if intensity is low
  } else {
    digitalWrite(ledPin, LOW); // Turn LED OFF if intensity is sufficient
  }

  delay(2000); // Wait 2 seconds before taking the next reading
}

void reconnect() {
  // Reconnect to MQTT broker if disconnected
  while (!client.connected()) {
    if (client.connect("ESP32Client")) {
      Serial.println("Connected to MQTT broker");
    } else {
      delay(5000); // Retry every 5 seconds if connection fails
    }
  }
}
