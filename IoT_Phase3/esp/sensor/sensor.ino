#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "Yuan";
const char* password = "Maymaysa123";
const char* mqtt_server = "192.168.171.150";
WiFiClient espClient;
PubSubClient client(espClient);


const char* topic = "light/data";


const int photoresistorPin = 32;
const int ledPin = 27;

void setup() {
  pinMode(photoresistorPin, INPUT);
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
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


  int lightIntensity = analogRead(photoresistorPin);
  Serial.print("Light Intensity: ");
  Serial.println(lightIntensity);

  char message[50];
  snprintf(message, 50, "%d", lightIntensity);
  client.publish(topic, message);
  
  if(lightIntensity<400){
  digitalWrite(ledPin,HIGH);
  }else{
  digitalWrite(ledPin,LOW);
  }
  
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