#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==========================================
// CONFIG
// ==========================================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverName = "http://<RPI_IP_ADDRESS>:5000/consume_action"; 

const int motor1Pin1 = 26; 
const int motor1Pin2 = 27; 
const int motor2Pin1 = 14; 
const int motor2Pin2 = 12; 

const int ledPin = 6;

const int ACTION_TIME_MS = 1000; 

void setup() {
  Serial.begin(115200);
  
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
  delay(100);
}

void executeAction(int actionCode) {
  switch(actionCode) {
    case 1: 
      digitalWrite(motor1Pin1, HIGH); digitalWrite(motor1Pin2, LOW);
      digitalWrite(motor2Pin1, HIGH); digitalWrite(motor2Pin2, LOW);
      break;
    case 2:
      digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, HIGH);
      digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, HIGH);
      break;
    case 3: 
      digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, HIGH);
      digitalWrite(motor2Pin1, HIGH); digitalWrite(motor2Pin2, LOW);
      break;
    case 4:
      digitalWrite(motor1Pin1, HIGH); digitalWrite(motor1Pin2, LOW);
      digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, HIGH);
      break;
    case 5:
      digitalWrite(ledPIN, HIGH);
      break;
  }
}

void stopMotors() {
  digitalWrite(motor1Pin1, LOW); digitalWrite(motor1Pin2, LOW);
  digitalWrite(motor2Pin1, LOW); digitalWrite(motor2Pin2, LOW);
}