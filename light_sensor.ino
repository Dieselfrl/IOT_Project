#define LIGHT_SENSOR_PIN 36 // ESP32 pin GPIO36 (ADC0) connected to light sensor
#define LED_PIN 22          // ESP32 pin GPIO22 connected to LED
#define LIGHT_THRESHOLD 400 // Threshold for turning the LED on or off

void setup()
{
    // Initialize serial communication at 9600 bits per second
    Serial.begin(9600);

    // Set the ADC attenuation to 11 dB (up to ~3.3V input)
    analogSetAttenuation(ADC_11db);

    // Set ESP32 pin to output mode for the LED
    pinMode(LED_PIN, OUTPUT);
}

void loop()
{
    // Read the value on the analog pin (value between 0 and 4095)
    int analogValue = analogRead(LIGHT_SENSOR_PIN);

    // Print the analog value
    Serial.print("Analog Value = ");
    Serial.print(analogValue);

    // Determine light intensity and print the description
    if (analogValue < 40)
    {
        Serial.println(" => Dark");
    }
    else if (analogValue < 800)
    {
        Serial.println(" => Dim");
    }
    else if (analogValue < 2000)
    {
        Serial.println(" => Light");
    }
    else if (analogValue < 3200)
    {
        Serial.println(" => Bright");
    }
    else
    {
        Serial.println(" => Very Bright");
    }

    // Control the LED based on the light intensity threshold
    if (analogValue < LIGHT_THRESHOLD)
    {
        digitalWrite(LED_PIN, HIGH); // Turn on LED
    }
    else
    {
        digitalWrite(LED_PIN, LOW); // Turn off LED
    }

    delay(500); // Delay for 500 milliseconds
}
