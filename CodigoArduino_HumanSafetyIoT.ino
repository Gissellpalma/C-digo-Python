#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <RTClib.h>

// Definición de pines
const int pirPin = 13;
const int smokePin = 12;
const int buzzerPin = 27;
const int relayPin = 14;

// Configuración de red y MQTT
const char* ssid = "SecurtyDomotic";
const char* password = "$3CUR171.38";
const char* mqtt_server = "192.168.2.8";

// Objetos
WiFiClient espClient;
PubSubClient client(espClient);
RTC_DS3231 rtc;

// Variables de control
bool pirEnabled = true;
bool humoEnabled = true;
bool motionCamara = false;
unsigned long lastPublish = 0;
const long publishInterval = 1000; 

unsigned long lastRtcPublishTime = 0;
const long rtcPublishInterval = 1000; // Publicar la hora cada segundo

DateTime ajustarHoraEcuador(DateTime fechaUTC) {
  if (fechaUTC.year() < 2000) {
    Serial.println("Fecha del RTC no válida. Ajustando a una fecha arbitraria.");
    fechaUTC = DateTime(2023, 7, 9, fechaUTC.hour(), fechaUTC.minute(), fechaUTC.second());
  }
  TimeSpan ajuste(-5, 0, 0, 0); // -5 horas para Ecuador
  return fechaUTC + ajuste;
}

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  if (String(topic) == "camara/control") {
    if (message == "on") {
      pirEnabled = false;
      motionCamara = true;
      client.publish("camara/estado", "Camara en modo programado");
    } else if (message == "off") {
      pirEnabled = true;
      motionCamara = false;
      client.publish("camara/estado", "Detectando Movimiento");
    }
    publishState();
  }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32Client")) {
      client.subscribe("camara/control");
      client.subscribe("camara/horario");
      client.subscribe("movimiento/ubicado");
      client.subscribe("movimiento/detectado");
      client.subscribe("movimiento/valor");
      client.subscribe("humo/detectado");
      client.subscribe("humo/valor");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  pinMode(pirPin, INPUT_PULLUP);
  pinMode(smokePin, INPUT);
  pinMode(relayPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  setup_wifi();
  client.setServer(mqtt_server, 1888);
  client.setCallback(callback);

  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }
  if (rtc.lostPower()) {
    Serial.println("RTC lost power, lets set the time!");
    rtc.adjust(DateTime(F(_DATE), F(TIME_)));
  }
  Wire.begin();
}

void publishState() {
  if (pirEnabled) {
    int motionDetected = digitalRead(pirPin);
    
    if (motionDetected == HIGH) {
      client.publish("movimiento/detectado", "ON");
      client.publish("movimiento/valor", "1");
    } else {
      client.publish("movimiento/detectado", "OFF");
      client.publish("movimiento/valor", "0");
    }
  } else {
    client.publish("movimiento/valor", "0");
  }
  
  if (motionCamara){


  }
  
  if (humoEnabled) {
    int smokeDetected = digitalRead(smokePin);
    
    if (smokeDetected == HIGH) {
      client.publish("humo/detectado", "ON");
      client.publish("humo/valor", "1");
       // Activar relé y buzzer
      digitalWrite(relayPin, HIGH);
      digitalWrite(buzzerPin, HIGH);
    } else {
      client.publish("humo/detectado", "OFF");
      client.publish("humo/valor", "0");
      // Desactivar relé y buzzer
      digitalWrite(relayPin, LOW);
      digitalWrite(buzzerPin, LOW);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long currentMillis = millis();
  if (currentMillis - lastPublish >= publishInterval) {
    lastPublish = currentMillis;
    publishState();
  }

  // Publicar la hora por MQTT cada segundo
  DateTime now = ajustarHoraEcuador(rtc.now());
  if (currentMillis - lastRtcPublishTime >= rtcPublishInterval) {
    lastRtcPublishTime = currentMillis;
    char dateTimeStr[20];
    snprintf(dateTimeStr, sizeof(dateTimeStr), "%04d-%02d-%02d %02d:%02d:%02d", 
             now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
    client.publish("Hora/Camara", dateTimeStr);
  }
}
