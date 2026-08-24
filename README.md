# 🛁 Sistema Baño Domótico

Proyecto de la Universidad Militar Nueva Granada — Ingeniería Mecatrónica.

Sistema de control para un baño inteligente que permite manejar iluminación,
ducha y persiana mediante **comandos de voz o texto en lenguaje natural**,
usando un microcontrolador **ESP32**, el protocolo **MQTT** y un modelo de
lenguaje (**Groq**) para interpretar lo que pide el usuario.

Se puede controlar desde:
- Una **consola de PC** (`chatbot_bano.py`)
- El **navegador del celular**, con un dashboard táctil y botón de micrófono
  (`app.py` + `templates/index.html`)

---

## 📐 Arquitectura general

```
[Usuario habla o escribe]
        │
        ▼
┌─────────────────────┐        ┌───────────────────┐
│  chatbot_bano.py     │        │      app.py        │
│  (consola)           │        │  (servidor Flask)  │
└──────────┬───────────┘        └─────────┬─────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
                  ┌───────────────┐
                  │  bano_core.py  │   <- lógica compartida
                  └───────┬───────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      API Groq (interpreta       Broker MQTT público
      texto/voz → comando)       (broker.hivemq.com)
                                        │
                                        ▼
                              ┌──────────────────┐
                              │   ESP32           │
                              │ DuchaInteligente.ino│
                              └──────────────────┘
                                        │
                         LEDs, servo (persiana), sensor DHT11
```

**Idea clave:** toda la lógica de conexión MQTT y de interpretación de
lenguaje natural vive en un solo archivo (`bano_core.py`) para no
duplicarla entre la versión de consola y la versión web. Tanto
`chatbot_bano.py` como `app.py` solo se encargan de la interfaz
(consola o navegador) y llaman a las funciones de `bano_core.py`.

---

## 📁 Estructura del repositorio

```
Sistema-Bano-Domotico/
├── app.py                  # Servidor Flask (control desde el celular)
├── bano_core.py             # Lógica compartida: MQTT, Groq, Whisper
├── chatbot_bano.py          # Chatbot de consola
├── DuchaInteligente.ino      # Firmware del ESP32
├── templates/
│   └── index.html            # Interfaz móvil (HTML+CSS+JS)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Requisitos

- Python 3.10+
- Una cuenta en [Groq](https://console.groq.com/) para obtener una API key
  gratuita (se usa para interpretar comandos y transcribir voz)
- Un ESP32 con los componentes: LEDs, sensor DHT11, micro-servo
- Arduino IDE (o PlatformIO) con las librerías: `DHT sensor library`,
  `ESP32Servo`, `PubSubClient`

Instalación de dependencias de Python:

```bash
pip install -r requirements.txt
```

Definir la API key de Groq como variable de entorno antes de correr
cualquiera de los dos programas:

```bash
# PowerShell
$env:GROQ_API_KEY = "tu_api_key_aqui"

# CMD
set GROQ_API_KEY=tu_api_key_aqui
```

---

## ▶️ Cómo correrlo

**Opción 1 — Consola:**
```bash
python chatbot_bano.py
```

**Opción 2 — Desde el celular (misma red WiFi):**
```bash
python app.py
```
Te dará una URL tipo `https://<IP-de-tu-PC>:5000` para abrir desde el
navegador del celular. El certificado será autofirmado (aparece una
advertencia, es normal — es tu propio servidor).

---

## 📦 Dependencias: qué es cada una y en qué archivo se usa

Esta sección explica, librería por librería, para qué sirve y en qué
parte exacta del proyecto se usa. Se separan las que van en
`requirements.txt` (se instalan con `pip`) de las que ya vienen incluidas
con Python o son propias de Arduino/el navegador.

### Instalables con `pip` (están en `requirements.txt`)

| Librería | Se usa en | Para qué exactamente |
|---|---|---|
| **`flask`** | `app.py` | Framework del servidor web. Provee `Flask(__name__)` para crear la app, `render_template()` para servir `index.html`, `request` para leer lo que envía el celular (texto o audio), `jsonify()` para responder en formato JSON, y el decorador `@app.route()` para definir cada URL (`/api/comando`, `/api/estado`, etc.) |
| **`pyopenssl`** | `app.py` | No se importa con `import`, pero es requerida por Flask internamente cuando se le pide `ssl_context="adhoc"` en `app.run(...)`. Esa opción genera un certificado HTTPS autofirmado al vuelo; sin `pyOpenSSL` instalado, esa línea falla. Es necesaria porque los navegadores solo dan acceso al micrófono en páginas seguras (HTTPS) |
| **`paho-mqtt`** | `bano_core.py` | Implementa el protocolo MQTT en Python (se importa como `paho.mqtt.client`). Se usa para crear el cliente (`mqtt.Client(...)`), conectarse al broker (`connect_async`), suscribirse al topic de estado (`subscribe`), publicar comandos al ESP32 (`publish`), y manejar reconexión automática (`loop_start`, `reconnect_delay_set`) |
| **`requests`** | `bano_core.py` | Cliente HTTP para hablar con la API de Groq. Se usa en `interpretar_mensaje()` (para mandar el texto del usuario al modelo de lenguaje) y en `transcribir_audio()` (para mandar el archivo de audio al modelo de transcripción Whisper) |

### Incluidas con Python (NO van en `requirements.txt`)

| Librería | Se usa en | Para qué |
|---|---|---|
| `os` | `bano_core.py` | Leer la variable de entorno `GROQ_API_KEY` con `os.environ.get(...)` |
| `re` | `bano_core.py` | Expresiones regulares para extraer temperatura y humedad de los mensajes de texto que manda el ESP32 (ej. `"Temp: 23.50 C"`) |
| `time` | `bano_core.py` | Pausas (`time.sleep(...)`) entre reintentos de conexión y entre el envío de comandos múltiples |
| `logging` | `app.py` | Apagar los logs automáticos de Flask/Werkzeug (una línea por cada petición HTTP), dejando solo los mensajes de error reales |
| `socket` | `app.py` | Truco para detectar la IP local del PC en la red (`obtener_ip_local()`), abriendo un socket UDP hacia una IP externa solo para que el sistema operativo elija la interfaz de red correcta |

### `chatbot_bano.py`

No usa ninguna librería externa nueva. Solo importa el propio módulo del
proyecto:
```python
import bano_core as core
```
Todo lo demás que usa (`input()`, `print()`) son funciones nativas del
lenguaje, no requieren instalación.

### `templates/index.html`

No usa `pip install` de nada — es JavaScript que corre **en el navegador
del celular**, no en el servidor de Python. Usa únicamente APIs nativas
del navegador:
- **`fetch()`** — para llamar a las rutas de Flask (`/api/comando`, `/api/estado`, etc.)
- **`MediaRecorder`** — para grabar audio del micrófono
- **`SpeechSynthesisUtterance` / `speechSynthesis`** — para leer en voz alta las confirmaciones (texto a voz)
- **`localStorage`** — para recordar si el usuario dejó activada o no la respuesta por voz

### `DuchaInteligente.ino`

No usa `pip`, usa librerías de Arduino/ESP32 que se instalan desde el
Arduino IDE (Herramientas → Administrar Bibliotecas), **no** con
`requirements.txt`:

| Librería | Para qué |
|---|---|
| `Arduino.h` | Funciones base del framework Arduino (`digitalWrite`, `delay`, etc.) |
| `DHT.h` | Leer el sensor de temperatura/humedad DHT11 |
| `ESP32Servo.h` | Controlar el servomotor de la persiana |
| `WiFi.h` | Conectar el ESP32 a la red WiFi |
| `PubSubClient.h` | Cliente MQTT para el ESP32 (equivalente en C++ a `paho-mqtt` en Python) |

---

## 🧩 Explicación del código, función por función

### 1. `bano_core.py` — el cerebro compartido

#### Configuración MQTT
```python
BROKER = "broker.hivemq.com"
PUERTO = 1883
TOPIC_PREFIJO = "unimilitar_duchainteligente_hearvl2026"
TOPIC_COMANDO = f"{TOPIC_PREFIJO}/comando"
TOPIC_ESTADO = f"{TOPIC_PREFIJO}/estado"
```
Se usa un broker MQTT **público**, así que se define un prefijo único de
topic para no chocar con otros proyectos que usen el mismo broker. Este
mismo prefijo debe coincidir exactamente con el que está en el `.ino`.
`TOPIC_COMANDO` es el canal por donde Python le manda órdenes al ESP32;
`TOPIC_ESTADO` es el canal por donde el ESP32 reporta lo que va pasando
(qué luz está encendida, la temperatura, etc.).

#### Configuración de Groq y el prompt del sistema
```python
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELO = "openai/gpt-oss-120b"
GROQ_TRANSCRIPCION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODELO_VOZ = "whisper-large-v3-turbo"
```
La API key nunca queda escrita en el código: se lee desde una variable de
entorno, así puedes compartir el repositorio en GitHub sin exponer tu
clave. Se definen dos endpoints distintos de Groq: uno para chat (texto →
comando) y otro para transcripción de audio (voz → texto).

```python
COMANDOS_VALIDOS = [
    "diurno", "nocturno", "sauna", "encender ducha", "apagar ducha",
    "abrir persiana", "cerrar persiana", "temperatura", "humedad", "estado",
]
MODOS_ILUMINACION_EXCLUYENTES = {"diurno", "nocturno", "sauna"}
PROMPT_SISTEMA = f"""Eres un intérprete de comandos..."""
```
`COMANDOS_VALIDOS` es la lista cerrada de acciones que el sistema entiende
— cualquier cosa fuera de esta lista se descarta. `PROMPT_SISTEMA` es el
texto que se le manda al modelo de lenguaje explicándole exactamente cómo
debe mapear frases en español natural (ej. "quiero dormir" → `"nocturno"`)
a esos comandos exactos, incluyendo la regla de que puede devolver varios
comandos separados por comas si el usuario pide más de una acción, y que
los tres modos de luz son mutuamente excluyentes.

#### Estado del baño
```python
ESTADO_ACTUAL = {
    "luz": None, "ducha": None, "persiana": None,
    "temperatura": None, "humedad": None,
}
```
Diccionario en memoria que guarda el último estado conocido del baño,
para que `app.py` pueda mostrarlo en el dashboard sin tener que preguntar
al ESP32 cada vez.

```python
def _actualizar_estado_desde_mensaje(mensaje: str):
```
Cada vez que llega un mensaje del ESP32 (ej. `"Modo DIURNO activado"`,
`"Ducha ENCENDIDA"`, `"Temp: 23.50 C | Hum: 45.00 %"`), esta función lo
analiza con `if/elif` y expresiones regulares (`re.search`) para
actualizar los campos correspondientes de `ESTADO_ACTUAL`.

```python
def obtener_estado() -> dict:
```
Devuelve una copia de `ESTADO_ACTUAL` más el campo `mqtt_conectado`, para
que `app.py` la sirva directamente como JSON en la ruta `/api/estado`.

#### Callbacks de conexión MQTT
```python
def al_conectar(client, userdata, flags, reason_code, properties=None):
def al_desconectar(client, userdata, flags, reason_code, properties=None):
def al_recibir_mensaje(client, userdata, msg):
```
Son funciones que la librería `paho-mqtt` llama automáticamente en
distintos eventos: `al_conectar` se dispara al lograr conexión con el
broker (y ahí se hace la suscripción al topic de estado);
`al_desconectar` marca la bandera `mqtt_conectado = False` si se pierde la
conexión; `al_recibir_mensaje` se dispara cada vez que llega un mensaje al
topic suscrito, y llama a `_actualizar_estado_desde_mensaje`.

```python
mqtt_client.on_connect = al_conectar
mqtt_client.on_disconnect = al_desconectar
mqtt_client.on_message = al_recibir_mensaje
mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
```
Aquí se "engancha" cada callback a su evento correspondiente, y se
configura que, si se pierde la conexión, los reintentos empiecen esperando
1 segundo y vayan aumentando hasta un máximo de 30 segundos entre intento
e intento (para no saturar al broker).

#### Conexión y envío de comandos
```python
def esta_conectado_mqtt() -> bool:
```
Devuelve simplemente el valor actual de la bandera `mqtt_conectado`, para
que otros archivos puedan consultar el estado de conexión sin acceder
directamente a la variable interna.

```python
def conectar_mqtt():
    mqtt_client.connect_async(BROKER, PUERTO, keepalive=60)
    mqtt_client.loop_start()
```
Inicia la conexión de forma **asíncrona** (no bloqueante): si el broker
tarda o falla, el programa no se congela. `loop_start()` lanza un hilo en
segundo plano que mantiene la conexión viva y reintenta solo,
indefinidamente. Después, la función espera hasta 8 segundos
(`SEGUNDOS_ESPERA_CONEXION_INICIAL`) a que se confirme la conexión antes
de seguir, solo para dar feedback inicial al usuario; si no conecta en ese
tiempo, avisa por consola pero el programa sigue funcionando (la conexión
se completará sola en segundo plano).

```python
def enviar_comando_esp32(comando: str):
```
Publica un solo comando en `TOPIC_COMANDO` usando
`mqtt_client.publish(...)`. Antes de intentar publicar, revisa que
`mqtt_conectado` sea `True`; si no, aborta y avisa el error. También
revisa el código de retorno de `publish()` para detectar fallos al
encolar el mensaje.

```python
def enviar_comandos_esp32(comandos: list[str]) -> bool:
```
Recorre una lista de comandos y llama a `enviar_comando_esp32()` para cada
uno, con una pequeña pausa (`SEGUNDOS_ENTRE_COMANDOS = 0.2`) entre cada
envío, para que el ESP32 no reciba todo de golpe cuando el usuario pide
varias acciones en un solo mensaje (ej. "enciende la ducha y abre la
persiana").

#### Interpretación de texto con Groq
```python
def _depurar_lista_comandos(comandos: list[str]) -> list[str]:
```
Limpia la respuesta cruda del modelo de lenguaje: recorre la lista de
strings, descarta cualquier palabra que no esté en `COMANDOS_VALIDOS`,
elimina duplicados, y si detecta más de un modo de luz mutuamente
excluyente en la misma respuesta (ej. el modelo devolvió `"diurno"` y
`"nocturno"` a la vez), se queda solo con el último de esos modos,
respetando la regla de exclusividad.

```python
def interpretar_mensaje(texto_usuario: str) -> list[str] | None:
```
Es la función principal de interpretación. Paso a paso:
1. Verifica que exista la API key; si no, avisa y devuelve `None`.
2. Arma el cuerpo de la petición HTTP con el prompt de sistema y el texto
   del usuario, usando `temperature=0` (respuestas deterministas, sin
   creatividad) y `reasoning_effort="low"` (respuesta rápida).
3. Intenta hasta 3 veces (`GROQ_MAX_REINTENTOS`) si hay timeout, error de
   red, o el servidor responde 429 (demasiadas peticiones) o 5xx (error
   del servidor), con espera exponencial entre intentos (1.5s, 3s, 6s).
4. Si la respuesta es 401, la API key es inválida — se detiene sin
   reintentar.
5. Si la respuesta es 200, extrae el contenido del mensaje, lo pasa a
   minúsculas, lo separa por comas, y lo limpia con
   `_depurar_lista_comandos()`.
6. Si el modelo respondió `"ninguno"` o la lista quedó vacía después de
   depurar, devuelve `None` (no se reconoció ningún comando).

#### Transcripción de voz
```python
def transcribir_audio(audio_bytes, nombre_archivo="audio.wav", mime="audio/wav") -> str | None:
```
Envía el audio grabado (bytes crudos) al endpoint de Whisper de Groq como
un archivo `multipart/form-data`, especificando `language="es"` y
`response_format="text"` para que la respuesta venga como texto plano
listo para pasarse directamente a `interpretar_mensaje()`. Maneja los
mismos casos de error que la función anterior (sin API key, 401, otros
códigos de error).

---

### 2. `chatbot_bano.py` — interfaz de consola

```python
def main():
    core.conectar_mqtt()
    while True:
        texto = input("Tú: ").strip()
        if texto.lower() == "salir":
            break
        comandos = core.interpretar_mensaje(texto)
        if not comandos:
            print("Bot: No logré identificar ningún comando válido...")
            continue
        core.enviar_comandos_esp32(comandos)
```
Es un loop simple de consola: primero conecta MQTT, luego entra en un
bucle infinito que lee lo que el usuario escribe con `input()`. Si escribe
`"salir"`, rompe el loop y termina. Si el texto está vacío, lo ignora y
vuelve a pedir entrada (`continue`). Si hay texto, lo manda a
`interpretar_mensaje()`; si no se reconoció ningún comando, avisa y
continúa; si sí, imprime qué va a ejecutar y llama a
`enviar_comandos_esp32()`.

```python
finally:
    core.mqtt_client.loop_stop()
    core.mqtt_client.disconnect()
```
Al terminar el programa (ya sea por `"salir"` o por `Ctrl+C`, capturado
con `except KeyboardInterrupt`), el bloque `finally` se asegura de cerrar
ordenadamente el hilo de MQTT y desconectar del broker, sin importar cómo
haya terminado el loop.

---

### 3. `app.py` — servidor web (Flask)

```python
logging.getLogger("werkzeug").setLevel(logging.ERROR)
```
Apaga el log automático de Flask (una línea por cada petición HTTP tipo
`127.0.0.1 - - [fecha] "POST /api/comando..."`), dejando la consola limpia
para solo mostrar los mensajes propios del programa.

```python
def obtener_ip_local() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()
```
Truco para obtener la IP del PC en la red local sin necesitar una
conexión real a internet: abre un socket UDP hacia una IP externa
(`8.8.8.8`, un DNS público de Google) solo para forzar al sistema
operativo a elegir qué interfaz de red usaría, y lee la IP local desde
ahí (`getsockname()`). Si algo falla, cae de vuelta a `"127.0.0.1"`.

```python
@app.route("/")
def index():
    return render_template("index.html")
```
Sirve la página principal — el dashboard móvil — desde la carpeta
`templates/`.

```python
@app.route("/api/comando", methods=["POST"])
def api_comando():
```
Recibe un JSON con un campo `"texto"`, valida que no esté vacío, lo pasa
por `core.interpretar_mensaje()`, y si se reconocieron comandos los envía
con `core.enviar_comandos_esp32()`. Devuelve un JSON con el resultado
(`ok`, `texto`, `comandos`, `mqtt_conectado`) para que el navegador
actualice la interfaz.

```python
@app.route("/api/comando-voz", methods=["POST"])
def api_comando_voz():
```
Igual que la ruta anterior, pero primero recibe un archivo de audio
(`request.files["audio"]`), lo transcribe con
`core.transcribir_audio()`, y luego sigue el mismo flujo: interpreta el
texto resultante y envía los comandos si se reconoció alguno.

```python
@app.route("/api/estado")
def api_estado():
    return jsonify(core.obtener_estado())
```
Ruta de solo lectura que el navegador consulta periódicamente para
repintar el dashboard con el último estado conocido del baño.

```python
@app.route("/api/refrescar", methods=["POST"])
def api_refrescar():
    enviado = core.enviar_comando_esp32("estado")
    return jsonify({"ok": enviado})
```
Le pide directamente al ESP32 que reporte su estado (sin pasar por Groq),
para refrescar temperatura y humedad en el dashboard sin gastar una
llamada a la API de lenguaje.

```python
if __name__ == "__main__":
    core.conectar_mqtt()
    ip_local = obtener_ip_local()
    ...
    app.run(host="0.0.0.0", port=5000, ssl_context="adhoc", debug=False)
```
Punto de entrada: conecta MQTT, calcula la IP local para mostrarla en
consola, y arranca el servidor Flask. `host="0.0.0.0"` hace que el
servidor sea visible desde otros dispositivos de la red (como el
celular), no solo desde el propio PC. `ssl_context="adhoc"` habilita
HTTPS autofirmado, necesario para que el navegador dé acceso al
micrófono.

---

### 4. `templates/index.html` — interfaz móvil

**Dashboard visual — pintado del estado:**
```javascript
function pintarDashboard(data) {
  document.getElementById('cardDiurno').classList.toggle('activa', data.luz === 'diurno');
  ...
}
```
Recibe el JSON de `/api/estado` y actualiza visualmente cada tarjeta:
resalta la tarjeta del modo de luz activo, cambia el texto y color del
badge de ducha/persiana, y actualiza los valores numéricos de temperatura
y humedad.

**Toques en las tarjetas — envío de comandos directos:**
```javascript
document.getElementById('cardDiurno').addEventListener('click', () => enviarTexto('diurno'));
```
Cada tarjeta de luz, al tocarla, llama a `enviarTexto()` con el comando
correspondiente directamente (sin pasar por reconocimiento de lenguaje
natural, ya que el texto ya es exactamente el comando válido).

**Botón de micrófono (push-to-talk):**
```javascript
mediaRecorder = new MediaRecorder(stream);
mediaRecorder.ondataavailable = (e) => chunksAudio.push(e.data);
mediaRecorder.onstop = async () => {
  const blob = new Blob(chunksAudio, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('audio', blob, 'comando.webm');
  const resp = await fetch('/api/comando-voz', { method: 'POST', body: formData });
  ...
};
```
Al presionar y mantener el botón (`touchstart`/`mousedown`), se pide
permiso de micrófono y se empieza a grabar con `MediaRecorder`. Al soltar
(`touchend`/`mouseup`), se detiene la grabación, se arma un `Blob` de
audio, y se envía como `FormData` a `/api/comando-voz`, donde el backend
lo transcribe e interpreta.

**Respuesta por voz (Text-to-Speech):**
```javascript
function hablar(texto) {
  if (!vozActiva || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(texto);
  utter.lang = 'es-ES';
  window.speechSynthesis.speak(utter);
}
```
Usa la API nativa del navegador para leer en voz alta la confirmación de
cada comando ejecutado. `FRASES_COMANDO` traduce el nombre técnico del
comando (ej. `"encender ducha"`) a una frase más natural para hablarla
(ej. `"Ducha encendida"`). El botón de altavoz en la esquina permite
activar/desactivar esta función, guardando la preferencia en
`localStorage` para que se recuerde entre visitas.

**Actualización periódica:**
```javascript
setInterval(actualizarEstado, 5000);
setInterval(refrescarSensores, 20000);
```
El dashboard consulta `/api/estado` cada 5 segundos (para reflejar
cambios hechos desde otro dispositivo, por ejemplo), y cada 20 segundos le
pide al ESP32, vía `/api/refrescar`, que reporte temperatura y humedad
actualizadas.

---

### 5. `DuchaInteligente.ino` — firmware del ESP32

**Conexión WiFi con reconexión no bloqueante:**
```cpp
void conectarWiFi() { ... }       // conexión inicial, con timeout de 15s
void gestionarWiFi() {
  if (WiFi.status() == WL_CONNECTED) { ... return; }
  // reintenta cada INTERVALO_RECONEXION_WIFI (10s) sin bloquear el loop()
}
```
`gestionarWiFi()` se llama en cada vuelta del `loop()`. Si el router se
reinicia o hay un corte de señal, el ESP32 reintenta conectarse solo cada
10 segundos, sin usar `delay()` bloqueante que congelaría el resto del
sistema (sensores, MQTT, etc.).

**Modos de luz mutuamente excluyentes:**
```cpp
void apagarLuces() { /* apaga diurno, nocturno y sauna */ }
void modoDiurno() { apagarLuces(); digitalWrite(LED_BLANCO_1, HIGH); ... }
void modoNocturno() { apagarLuces(); ... }
void modoSauna() { apagarLuces(); ... }
```
Antes de encender cualquier modo de iluminación, siempre se apagan todos
los demás con `apagarLuces()`. Esto garantiza que nunca queden dos modos
activos a la vez, sin importar el orden en que lleguen los comandos desde
Python.

**Ducha:**
```cpp
void encenderDucha() { digitalWrite(LED_DUCHA_1, HIGH); digitalWrite(LED_DUCHA_2, HIGH); ... }
void apagarDucha() { digitalWrite(LED_DUCHA_1, LOW); digitalWrite(LED_DUCHA_2, LOW); ... }
```
Enciende o apaga los pines correspondientes y publica el nuevo estado en
`TOPIC_ESTADO` para que Python lo registre.

**Persiana con servomotor:**
```cpp
void abrirPersiana() { persiana.write(165); ... }
void cerrarPersiana() { persiana.write(75); ... }
```
El servo se mueve a un ángulo fijo para cada posición: 165° para abierta,
75° para cerrada.

**Sensor DHT11 con lectura no bloqueante:**
```cpp
void leerDHT11() {
  if (millis() - ultimaLectura < INTERVALO_DHT) return;
  ultimaLectura = millis();
  float nuevaHumedad = dht.readHumidity();
  float nuevaTemperatura = dht.readTemperature();
  if (isnan(nuevaHumedad) || isnan(nuevaTemperatura)) { ... return; }
  humedad = nuevaHumedad;
  temperatura = nuevaTemperatura;
}
```
Se evita leer el sensor en cada vuelta del loop (el DHT11 es demasiado
lento para eso); solo se lee cada `INTERVALO_DHT` (2 segundos), y se
valida con `isnan()` que la lectura no haya fallado antes de guardarla.

**Procesamiento de comandos:**
```cpp
void procesarComando(String comando) {
  comando.trim();
  comando.toLowerCase();
  if (comando == "diurno") { modoDiurno(); }
  else if (comando == "nocturno") { modoNocturno(); }
  ...
  else { Serial.println("Comando no reconocido."); }
}
```
Recibe el string del comando (venga de MQTT o del monitor serial), lo
normaliza (quita espacios sobrantes, pasa a minúsculas), y lo compara
contra cada comando válido con una cadena de `if/else if` para ejecutar la
acción correspondiente.

**Callback MQTT:**
```cpp
void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  String mensaje;
  for (unsigned int i = 0; i < length; i++) { mensaje += (char)payload[i]; }
  procesarComando(mensaje);
}
```
Se ejecuta automáticamente cada vez que llega un mensaje al topic
suscrito (`TOPIC_COMANDO`). El payload llega como bytes crudos, así que
este bucle lo reconstruye caracter por caracter en un `String`, y lo pasa
a `procesarComando()`.

**Reconexión MQTT:**
```cpp
void reconectarMQTT() {
  while (!mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
    String clientId = "ESP32DuchaInteligente-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      mqttClient.subscribe(TOPIC_COMANDO);
      mqttClient.publish(TOPIC_ESTADO, "ESP32 conectado y listo");
    } else {
      delay(5000);
    }
  }
}
```
Genera un ID de cliente aleatorio (`clientId`) en cada intento, para
evitar colisiones con otros dispositivos conectados al mismo broker
público (si dos dispositivos usan el mismo ID, uno desconecta al otro).
Si falla la conexión, espera 5 segundos antes de reintentar.

**`setup()` y `loop()`:**
```cpp
void setup() {
  // configura pines, sensores, servo, WiFi, MQTT
  modoDiurno(); // estado inicial
}

void loop() {
  gestionarWiFi();
  if (WiFi.status() == WL_CONNECTED) {
    if (!mqttClient.connected()) { reconectarMQTT(); }
    mqttClient.loop();
  }
  leerDHT11();
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    procesarComando(comando);
  }
  delay(20);
}
```
`setup()` corre una sola vez al encender el ESP32: prepara todos los
pines y periféricos, y deja el sistema en modo diurno por defecto.
`loop()` corre indefinidamente: gestiona WiFi, mantiene viva la conexión
MQTT (`mqttClient.loop()` procesa mensajes entrantes/salientes), lee el
sensor, y también acepta comandos escritos directamente por el monitor
serial (útil para pruebas sin depender de la red).

---

## 🔒 Nota de seguridad

`broker.hivemq.com` es un broker MQTT **público y sin autenticación**.
Cualquiera que conozca el prefijo de topic (`unimilitar_duchainteligente_hearvl2026`)
podría enviar comandos al sistema. Para un proyecto académico de
demostración esto es aceptable, pero para un uso real se recomendaría un
broker privado con usuario/contraseña o TLS.

---

## 👤 Autor

Proyecto desarrollado por Julián — Ingeniería Mecatrónica, Universidad
Militar Nueva Granada.
