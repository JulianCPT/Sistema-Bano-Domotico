#include <Arduino.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <PubSubClient.h>

// =====================================================
// WIFI Y MQTT
// =====================================================

const char* WIFI_SSID     = "Samsung A35 5G JULIAN";
const char* WIFI_PASSWORD = "julian310";

const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PUERTO = 1883;

// Prefijo único del proyecto. broker.hivemq.com es PÚBLICO y lo usan miles
// de personas: un topic genérico como "duchainteligente/comando" puede
// chocar con el de alguien más. Cambia este prefijo por algo propio
// (ej. tu usuario de la universidad, un código de grupo, etc.) y usa
// EXACTAMENTE el mismo prefijo en chatbot_bano.py.
const char* TOPIC_COMANDO = "unimilitar_duchainteligente_hearvl2026/comando";
const char* TOPIC_ESTADO  = "unimilitar_duchainteligente_hearvl2026/estado";

WiFiClient espClient;
PubSubClient mqttClient(espClient);


// =====================================================
// PINES
// =====================================================

// ---------- ILUMINACIÓN DIURNA ----------
#define LED_BLANCO_1 25
#define LED_BLANCO_2 26
#define LED_BLANCO_3 27

// ---------- ILUMINACIÓN NOCTURNA ----------
#define LED_NOCHE_1 14
#define LED_NOCHE_2 16

// ---------- ILUMINACIÓN SAUNA ----------
#define LED_SAUNA_1 32
#define LED_SAUNA_2 33

// ---------- DUCHA ----------
#define LED_DUCHA_1 18
#define LED_DUCHA_2 19

// ---------- DHT11 ----------
#define DHT_PIN 4
#define DHT_TYPE DHT11

// ---------- SERVO ----------
#define SERVO_PIN 13


// =====================================================
// OBJETOS
// =====================================================

DHT dht(DHT_PIN, DHT_TYPE);
Servo persiana;


// =====================================================
// VARIABLES
// =====================================================

unsigned long ultimaLectura = 0;
const unsigned long INTERVALO_DHT = 2000;

float temperatura = 0.0;
float humedad = 0.0;

// ---------- RECONEXIÓN WIFI ----------
unsigned long ultimoIntentoWiFi = 0;
const unsigned long INTERVALO_RECONEXION_WIFI = 10000; // esperar 10s entre intentos
bool wifiConectadoAnteriormente = false;


// =====================================================
// WIFI
// =====================================================

void escanearRedes() {
  Serial.println();
  Serial.println("===== ESCANEANDO REDES WIFI CERCANAS =====");

  int numRedes = WiFi.scanNetworks();

  if (numRedes == 0) {
    Serial.println("No se encontró ninguna red WiFi cerca.");
  } else {
    for (int i = 0; i < numRedes; i++) {
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(WiFi.SSID(i));
      Serial.print(" (canal ");
      Serial.print(WiFi.channel(i));
      Serial.print(", RSSI ");
      Serial.print(WiFi.RSSI(i));
      Serial.println(")");
    }
  }

  Serial.println("===========================================");
  Serial.println();
}


void conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);

  escanearRedes();

  Serial.print("Conectando a WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 30) {
    delay(500);
    Serial.print(".");
    intentos++;
  }

  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("ERROR: No se pudo conectar al WiFi después de 15 segundos.");
    Serial.print("Estado actual: ");
    Serial.println(WiFi.status());
    Serial.println("Revisa el nombre/contraseña de la red, o si es de 5GHz.");
    Serial.println("El sistema seguirá intentando reconectar en segundo plano.");
    return;
  }

  wifiConectadoAnteriormente = true;
  Serial.print("WiFi conectado. IP: ");
  Serial.println(WiFi.localIP());
}


// =====================================================
// RECONEXIÓN WIFI (no bloqueante)
// Se llama en cada vuelta del loop(). Si el WiFi se cae
// (router se reinicia, señal débil, corte del ISP, etc.),
// esto reintenta conectar sin congelar el resto del sistema
// ni bombardear el router con intentos constantes.
// =====================================================

void gestionarWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiConectadoAnteriormente) {
      wifiConectadoAnteriormente = true;
      Serial.print("WiFi reconectado. IP: ");
      Serial.println(WiFi.localIP());
    }
    return;
  }

  // Se perdió la conexión
  if (wifiConectadoAnteriormente) {
    wifiConectadoAnteriormente = false;
    Serial.println("Se perdió la conexión WiFi. Intentando reconectar...");
  }

  unsigned long ahora = millis();
  if (ahora - ultimoIntentoWiFi >= INTERVALO_RECONEXION_WIFI) {
    ultimoIntentoWiFi = ahora;
    Serial.println("Reintentando conexión WiFi...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
}


// =====================================================
// APAGAR TODAS LAS LUCES AMBIENTALES
// =====================================================

void apagarLuces() {
  digitalWrite(LED_BLANCO_1, LOW);
  digitalWrite(LED_BLANCO_2, LOW);
  digitalWrite(LED_BLANCO_3, LOW);

  digitalWrite(LED_NOCHE_1, LOW);
  digitalWrite(LED_NOCHE_2, LOW);

  digitalWrite(LED_SAUNA_1, LOW);
  digitalWrite(LED_SAUNA_2, LOW);
}


// =====================================================
// MODO DIURNO
// =====================================================

void modoDiurno() {
  apagarLuces();

  digitalWrite(LED_BLANCO_1, HIGH);
  digitalWrite(LED_BLANCO_2, HIGH);
  digitalWrite(LED_BLANCO_3, HIGH);

  Serial.println("Modo DIURNO activado");
  mqttClient.publish(TOPIC_ESTADO, "Modo DIURNO activado");
}


// =====================================================
// MODO NOCTURNO
// =====================================================

void modoNocturno() {
  apagarLuces();

  digitalWrite(LED_NOCHE_1, HIGH);
  digitalWrite(LED_NOCHE_2, HIGH);

  Serial.println("Modo NOCTURNO activado");
  mqttClient.publish(TOPIC_ESTADO, "Modo NOCTURNO activado");
}


// =====================================================
// MODO SAUNA
// =====================================================

void modoSauna() {
  apagarLuces();

  digitalWrite(LED_SAUNA_1, HIGH);
  digitalWrite(LED_SAUNA_2, HIGH);

  Serial.println("Modo SAUNA activado");
  mqttClient.publish(TOPIC_ESTADO, "Modo SAUNA activado");
}


// =====================================================
// DUCHA
// =====================================================

void encenderDucha() {
  digitalWrite(LED_DUCHA_1, HIGH);
  digitalWrite(LED_DUCHA_2, HIGH);

  Serial.println("Ducha ENCENDIDA");
  mqttClient.publish(TOPIC_ESTADO, "Ducha ENCENDIDA");
}


void apagarDucha() {
  digitalWrite(LED_DUCHA_1, LOW);
  digitalWrite(LED_DUCHA_2, LOW);

  Serial.println("Ducha APAGADA");
  mqttClient.publish(TOPIC_ESTADO, "Ducha APAGADA");
}


// =====================================================
// PERSIANA
// =====================================================
// 165° = posición abierta
// 75°  = posición cerrada
// =====================================================

void abrirPersiana() {
  persiana.write(165);
  Serial.println("Persiana ABIERTA");
  mqttClient.publish(TOPIC_ESTADO, "Persiana ABIERTA");
}


void cerrarPersiana() {
  persiana.write(75);
  Serial.println("Persiana CERRADA");
  mqttClient.publish(TOPIC_ESTADO, "Persiana CERRADA");
}


// =====================================================
// DHT11
// =====================================================

void leerDHT11() {
  if (millis() - ultimaLectura < INTERVALO_DHT) {
    return;
  }

  ultimaLectura = millis();

  float nuevaHumedad = dht.readHumidity();
  float nuevaTemperatura = dht.readTemperature();

  if (isnan(nuevaHumedad) || isnan(nuevaTemperatura)) {
    Serial.println("ERROR: No se pudo leer el DHT11");
    return;
  }

  humedad = nuevaHumedad;
  temperatura = nuevaTemperatura;

  Serial.println();
  Serial.println("===== SENSOR DHT11 =====");
  Serial.print("Temperatura: ");
  Serial.print(temperatura);
  Serial.println(" °C");
  Serial.print("Humedad: ");
  Serial.print(humedad);
  Serial.println(" %");
  Serial.println("========================");
}


// =====================================================
// PROCESAMIENTO DE COMANDOS
// (misma lógica original, ahora alimentada por MQTT o Serial)
// =====================================================

void procesarComando(String comando) {
  comando.trim();
  comando.toLowerCase();

  if (comando == "diurno") {
    modoDiurno();
  }
  else if (comando == "nocturno") {
    modoNocturno();
  }
  else if (comando == "sauna") {
    modoSauna();
  }
  else if (comando == "encender ducha") {
    encenderDucha();
  }
  else if (comando == "apagar ducha") {
    apagarDucha();
  }
  else if (comando == "abrir persiana") {
    abrirPersiana();
  }
  else if (comando == "cerrar persiana") {
    cerrarPersiana();
  }
  else if (comando == "temperatura") {
    String msg = "Temperatura: " + String(temperatura) + " C";
    Serial.println(msg);
    mqttClient.publish(TOPIC_ESTADO, msg.c_str());
  }
  else if (comando == "humedad") {
    String msg = "Humedad: " + String(humedad) + " %";
    Serial.println(msg);
    mqttClient.publish(TOPIC_ESTADO, msg.c_str());
  }
  else if (comando == "estado") {
    String msg = "Temp: " + String(temperatura) + " C | Hum: " + String(humedad) + " %";
    Serial.println();
    Serial.println("===== ESTADO DEL BANO =====");
    Serial.println(msg);
    Serial.println("===========================");
    mqttClient.publish(TOPIC_ESTADO, msg.c_str());
  }
  else {
    Serial.println("Comando no reconocido.");
    mqttClient.publish(TOPIC_ESTADO, "Comando no reconocido");
  }
}


// =====================================================
// CALLBACK MQTT
// Se ejecuta cada vez que llega un mensaje al topic suscrito
// =====================================================

void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  String mensaje;

  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }

  Serial.print("MQTT -> [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(mensaje);

  procesarComando(mensaje);
}


// =====================================================
// RECONEXIÓN MQTT
// =====================================================

void reconectarMQTT() {
  while (!mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.print("Conectando a MQTT...");

    // ID de cliente único (evita colisiones con otros dispositivos)
    String clientId = "ESP32DuchaInteligente-" + String(random(0xffff), HEX);

    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(" conectado");
      mqttClient.subscribe(TOPIC_COMANDO);
      Serial.print("Suscrito a: ");
      Serial.println(TOPIC_COMANDO);
      mqttClient.publish(TOPIC_ESTADO, "ESP32 conectado y listo");
    } else {
      Serial.print(" falló, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" reintentando en 5s");
      delay(5000);
    }
  }
}


// =====================================================
// SETUP
// =====================================================

void setup() {
  Serial.begin(115200);

  // ---------------------------------------------------
  // CONFIGURAR LEDs
  // ---------------------------------------------------

  pinMode(LED_BLANCO_1, OUTPUT);
  pinMode(LED_BLANCO_2, OUTPUT);
  pinMode(LED_BLANCO_3, OUTPUT);

  pinMode(LED_NOCHE_1, OUTPUT);
  pinMode(LED_NOCHE_2, OUTPUT);

  pinMode(LED_SAUNA_1, OUTPUT);
  pinMode(LED_SAUNA_2, OUTPUT);

  pinMode(LED_DUCHA_1, OUTPUT);
  pinMode(LED_DUCHA_2, OUTPUT);

  // ---------------------------------------------------
  // ESTADO INICIAL
  // ---------------------------------------------------

  apagarLuces();
  apagarDucha();

  // ---------------------------------------------------
  // DHT11
  // ---------------------------------------------------

  dht.begin();

  // ---------------------------------------------------
  // SERVO
  // ---------------------------------------------------

  persiana.setPeriodHertz(50);
  persiana.attach(SERVO_PIN, 500, 2400);
  persiana.write(75);  // Inicia cerrada

  // ---------------------------------------------------
  // WIFI Y MQTT
  // ---------------------------------------------------

  conectarWiFi();

  mqttClient.setServer(MQTT_BROKER, MQTT_PUERTO);
  mqttClient.setCallback(callbackMQTT);

  // ---------------------------------------------------
  // MENÚ
  // ---------------------------------------------------

  Serial.println();
  Serial.println("================================");
  Serial.println("       BANO INTELIGENTE");
  Serial.println("================================");
  Serial.println();
  Serial.println("Sistema iniciado correctamente.");
  Serial.println();
  Serial.println("COMANDOS DISPONIBLES:");
  Serial.println("diurno, nocturno, sauna, encender ducha,");
  Serial.println("apagar ducha, abrir persiana, cerrar persiana,");
  Serial.println("temperatura, humedad, estado");
  Serial.println();

  // Modo inicial
  modoDiurno();
}


// =====================================================
// LOOP
// =====================================================

void loop() {
  // Gestionar reconexión de WiFi (no bloqueante)
  gestionarWiFi();

  // Mantener conexión MQTT viva (solo si hay WiFi disponible)
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqttClient.connected()) {
      reconectarMQTT();
    }
    mqttClient.loop();
  }

  // Lectura del sensor
  leerDHT11();

  // Comandos por Serial (se mantienen para pruebas locales)
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    procesarComando(comando);
  }

  delay(20);
}
