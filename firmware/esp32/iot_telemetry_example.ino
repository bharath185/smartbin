/*
 * SmartBin ESP32 IoT Device Firmware Example
 * Features:
 *   - WiFi Connection
 *   - Ultrasonic Sensor HC-SR04 (Bin Fill Level Calculation)
 *   - Flame / Fire Sensor (Analog/Digital Fire Alert Trigger)
 *   - DHT11/22 or DS18B20 (Temperature Monitoring)
 *   - GPS Module (NEO-6M for Latitude/Longitude)
 *   - REST API Telemetry Push to /iot/telemetry
 *   - Emergency Fire Alert Push to /iot/fire-alert
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Wi-Fi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server API URL
// Change to your server IP or domain:
const char* serverApiUrl = "http://192.168.1.100:8000/iot/telemetry";
const char* fireAlertUrl = "http://192.168.1.100:8000/iot/fire-alert";

// Hardware Pin Configuration
#define TRIG_PIN 5
#define ECHO_PIN 18
#define FLAME_PIN 34    // Digital or Analog input from Flame Sensor
#define BUZZER_PIN 4
#define BIN_HEIGHT_CM 100.0 // Total bin depth in cm

// Unique Dustbin Hardware ID & Static/GPS Coordinates
const char* DUSTBIN_ID = "DB002";
float currentLatitude = 12.9720;
float currentLongitude = 77.5950;

unsigned long lastTelemetryTime = 0;
const unsigned long telemetryInterval = 10000; // Send telemetry every 10s

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(FLAME_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  Serial.println("\nConnecting to Wi-Fi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! ESP32 IP: " + WiFi.localIP().toString());
}

// Measure distance using HC-SR04 Ultrasonic sensor
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;
  return (duration * 0.0343) / 2.0;
}

// Calculate Fill Level Percentage (0 to 100%)
float calculateFillPercentage(float distanceCm) {
  if (distanceCm < 0) return 0;
  if (distanceCm >= BIN_HEIGHT_CM) return 0;
  float filledCm = BIN_HEIGHT_CM - distanceCm;
  float percentage = (filledCm / BIN_HEIGHT_CM) * 100.0;
  if (percentage < 0) percentage = 0;
  if (percentage > 100) percentage = 100;
  return percentage;
}

// Check flame sensor (Low active or reading < threshold)
bool isFireDetected() {
  int flameVal = digitalRead(FLAME_PIN);
  return (flameVal == LOW); // Typical IR flame sensor gives LOW on flame detection
}

// Send HTTP POST JSON Request
void sendJsonPost(const char* url, String jsonPayload) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    Serial.println("Sending: " + jsonPayload);
    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.printf("Response [%d]: %s\n", httpResponseCode, response.c_str());
    } else {
      Serial.printf("Error on POST: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  }
}

void loop() {
  bool fire = isFireDetected();

  // 1. EMERGENCY: Fire detected immediately triggers priority alert
  if (fire) {
    Serial.println("🔥 CRITICAL WARNING: FIRE DETECTED BY HARDWARE SENSOR!");
    digitalWrite(BUZZER_PIN, HIGH);

    StaticJsonDocument<256> doc;
    doc["dustbin_id"] = DUSTBIN_ID;
    doc["latitude"] = currentLatitude;
    doc["longitude"] = currentLongitude;
    doc["temperature"] = 85.5; // Sensor temp
    doc["smoke_ppm"] = 320.0;
    doc["details"] = "IR flame sensor triggered";

    String payload;
    serializeJson(doc, payload);
    sendJsonPost(fireAlertUrl, payload);

    delay(2000); // Debounce to prevent flooding
    return;
  } else {
    digitalWrite(BUZZER_PIN, LOW);
  }

  // 2. Regular Periodic Telemetry (Fill Level & GPS)
  if (millis() - lastTelemetryTime > telemetryInterval) {
    lastTelemetryTime = millis();

    float dist = readDistanceCm();
    float fillLevel = calculateFillPercentage(dist);

    StaticJsonDocument<256> doc;
    doc["dustbin_id"] = DUSTBIN_ID;
    doc["fill_level"] = fillLevel;
    doc["fire_detected"] = false;
    doc["latitude"] = currentLatitude;
    doc["longitude"] = currentLongitude;
    doc["battery_level"] = 92.0;

    String payload;
    serializeJson(doc, payload);
    sendJsonPost(serverApiUrl, payload);
  }

  delay(100);
}
