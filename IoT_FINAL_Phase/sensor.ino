#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// Define pins
#define RST_PIN 9
#define SS_PIN 10
#define DHT_PIN 2
#define PHOTORESISTOR_PIN A0
#define LED_PIN 5

// WiFi credentials
const char *ssid = "your_SSID";
const char *password = "your_PASSWORD";

// MQTT broker
const char *mqtt_server = "192.168.171.150";
const char *rfid_topic = "home/rfid";
const char *light_topic = "home/light";
const char *dht_topic = "home/dht";

WiFiClient espClient;
PubSubClient client(espClient);
MFRC522 mfrc522(SS_PIN, RST_PIN); // Create MFRC522 instance.
DHT dht(DHT_PIN, DHT11);

void setup()
{
    Serial.begin(115200);
    SPI.begin();        // Init SPI bus
    mfrc522.PCD_Init(); // Init MFRC522
    dht.begin();

    pinMode(PHOTORESISTOR_PIN, INPUT);
    pinMode(LED_PIN, OUTPUT);

    setup_wifi();
    client.setServer(mqtt_server, 1883);
}

void setup_wifi()
{
    delay(10);
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi connected");
}

void loop()
{
    if (!client.connected())
    {
        reconnect();
    }
    client.loop();

    readRFID();
    readDHT();
    readLightIntensity();

    delay(2000); // Adjust the delay as needed
}

void reconnect()
{
    while (!client.connected())
    {
        Serial.print("Attempting MQTT connection...");
        if (client.connect("ESP32Client"))
        {
            Serial.println("connected");
        }
        else
        {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

void readRFID()
{
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial())
    {
        return;
    }
    String content = "";
    for (byte i = 0; i < mfrc522.uid.size; i++)
    {
        content += String(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " ");
        content += String(mfrc522.uid.uidByte[i], HEX);
    }
    content.toUpperCase();
    Serial.println("RFID tag: " + content);
    client.publish(rfid_topic, content.c_str());
}

void readDHT()
{
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    if (isnan(h) || isnan(t))
    {
        Serial.println("Failed to read from DHT sensor!");
        return;
    }
    String dht_data = "Temperature: " + String(t) + " C, Humidity: " + String(h) + " %";
    Serial.println(dht_data);
    client.publish(dht_topic, dht_data.c_str());
}

void readLightIntensity()
{
    int light_value = analogRead(PHOTORESISTOR_PIN);
    Serial.println("Light Intensity: " + String(light_value));
    if (light_value < 400)
    {
        digitalWrite(LED_PIN, HIGH);
    }
    else
    {
        digitalWrite(LED_PIN, LOW);
    }
    client.publish(light_topic, String(light_value).c_str());
}
