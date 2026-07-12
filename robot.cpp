#include <WiFi.h> // Use <ESP8266WiFi.h> if using ESP8266
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==========================================
// CONFIGURATION
// ==========================================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverName = "http://<RPI_IP_ADDRESS>:5000/consume_action"; 

// Motor Driver Pins (Example for L298N)
const int motor1Pin1 = 26; 
const int motor1Pin2 = 27; 
const int motor2Pin1 = 14; 
const int motor2Pin2 = 12; 

const int ACTION_TIME_MS = 1000; // 1 second
// ==========================================

void setup() {
  Serial.begin(115200);
  
  // Set motor pins as outputs
  pinMode(motor1Pin1, OUTPUT);
  pinMode(motor1Pin2, OUTPUT);
  pinMode(motor2Pin1, OUTPUT);
  pinMode(motor2Pin2, OUTPUT);
  stopMotors();

  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  while(WiFi.status() != WL_CONNECTED) { 
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
}

void loop() {
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    http.begin(serverName);
    int httpResponseCode = http.GET();
    
    if (httpResponseCode > 0) {
      String payload = http.getString();
      
      // Parse JSON
      StaticJsonDocument<200> doc;
      deserializeJson(doc, payload);
      int action = doc["action"];

      if (action >= 1 && action <= 6) {
        Serial.print("Executing action: ");
        Serial.println(action);
        
        executeAction(action);
        delay(ACTION_TIME_MS);
        stopMotors();
      }
    }
    http.end();
  }
  delay(100); // Poll every 100ms
}

void executeAction(int actionCode) {
  // Define what each code does to the motors!
  switch(actionCode) {
    case 1: // Forward
      digitalWrite(motor1Pin1, HIGH); digitalWrite(motor1Pin2, LOW);
      digitalWrite(motor2Pin1, HIGH); digitalWrite(motor2Pin2, LOW);
      break;
    case 2: // Backward
      digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, HIGH);
      digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, HIGH);
      break;
    case 3: // Turn Left
      digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, HIGH);
      digitalWrite(motor2Pin1, HIGH); digitalWrite(motor2Pin2, LOW);
      break;
    case 4: // Turn Right
      digitalWrite(motor1Pin1, HIGH); digitalWrite(motor1Pin2, LOW);
      digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, HIGH);
      break;
    case 5: // Custom Action (e.g., spin one motor fast)
      digitalWrite(motor1Pin1, HIGH); digitalWrite(motor1Pin2, LOW);
      digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, LOW);
      break;
    case 6: // Custom Action
      digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, LOW);
      digitalWrite(motor2Pin1, HIGH); digitalWrite(motor2Pin2, LOW);
      break;
  }
}

void stopMotors() {
  digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, LOW);
}