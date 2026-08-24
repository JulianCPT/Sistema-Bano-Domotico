<div align="center">

# 🛁 Baño Domótico Inteligente

### Control de iluminación, ducha y persiana por voz o texto, con IA e IoT

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![ESP32](https://img.shields.io/badge/ESP32-Microcontrolador-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com/)
[![Flask](https://img.shields.io/badge/Flask-Servidor%20Web-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MQTT](https://img.shields.io/badge/MQTT-HiveMQ-660066?style=for-the-badge&logo=eclipsemosquitto&logoColor=white)](https://www.hivemq.com/)
[![Groq](https://img.shields.io/badge/Groq-LLM%20%2B%20Whisper-F55036?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com/)

**Universidad Militar Nueva Granada** · Ingeniería Mecatrónica

</div>

---

## 📸 Vista previa

<!--
  AQUÍ VAN TUS IMÁGENES. Sube tus capturas/fotos a una carpeta llamada
  "docs/imagenes" dentro del repo y referencia cada una así:

  ![Dashboard móvil](docs/imagenes/dashboard.png)

  Sugerencias de qué capturar:
  - Captura del dashboard en el celular (modos de luz, ducha, persiana)
  - Foto del ESP32 armado con los LEDs, el DHT11 y el servo
  - GIF corto usando el botón de micrófono y viendo el toast de respuesta
  - Captura de la consola (chatbot_bano.py) mostrando un comando interpretado
-->

<table>
  <tr>
    <td align="center" width="50%">
      <img src="docs/imagenes/dashboard.png" alt="Dashboard móvil" width="100%"><br>
      <sub><b>Dashboard móvil</b> — control táctil y por voz</sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/imagenes/montaje.png" alt="Montaje del ESP32" width="100%"><br>
      <sub><b>Montaje físico</b> — ESP32, sensores y actuadores</sub>
    </td>
  </tr>
</table>

<div align="center">
  <img src="docs/imagenes/demo.gif" alt="Demo funcionando" width="60%"><br>
  <sub><b>Demo:</b> comando de voz → interpretación → acción en el ESP32</sub>
</div>

---

## 📖 Descripción

Sistema de control para un baño inteligente que permite manejar **iluminación, ducha y persiana** mediante **comandos de voz o texto en lenguaje natural**. Combina un microcontrolador **ESP32**, el protocolo **MQTT** y un modelo de lenguaje (**Groq**) que interpreta lo que pide el usuario y lo traduce en acciones concretas.

Se puede controlar desde:
- 🖥️ Una **consola de PC** (`chatbot_bano.py`)
- 📱 El **navegador del celular**, con un dashboard táctil y botón de micrófono (`app.py` + `templates/index.html`)

---

## 📑 Tabla de contenido

- [Conceptos clave](#-conceptos-clave-para-entender-el-proyecto)
- [Arquitectura general](#-arquitectura-general)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Características](#-características)
- [Requisitos](#️-requisitos)
- [Instalación](#-instalación)
- [Cómo correrlo](#️-cómo-correrlo)
- [Explicación del código](#-explicación-del-código-bloque-por-bloque)
- [Comandos disponibles](#-comandos-disponibles)
- [Nota de seguridad](#-nota-de-seguridad)
- [Autor](#-autor)

---

## 📚 Conceptos clave (para entender el proyecto)

Si es la primera vez que ves términos como MQTT, broker o LLM, aquí tienes una explicación rápida de cada pieza antes de meterte al código.

> **Índice de esta sección:** [MQTT](#-qué-es-mqtt) · [Broker](#-qué-es-un-broker) · [Topic](#️-qué-es-un-topic) · [LLM y Groq](#-qué-es-un-llm-y-por-qué-se-usa-groq) · [Whisper](#️-qué-es-whisper) · [HTTPS](#-qué-es-https-y-por-qué-el-certificado-no-confiable) · [Puerto 5000](#-por-qué-el-puerto-5000) · [ESP32](#-qué-es-el-esp32-y-qué-hace-aquí) · [Variables de entorno](#-qué-son-las-variables-de-entorno-y-por-qué-la-api-key-no-va-en-el-código) · [API REST y JSON](#-qué-es-una-api-rest-y-qué-es-json) · [GPIO y DHT11](#-qué-son-los-pines-gpio-y-el-sensor-dht11) · [Servomotor y ángulos](#-cómo-funciona-el-servomotor-de-la-persiana) · [Código no bloqueante](#-por-qué-no-se-usa-delay-en-el-esp32-código-no-bloqueante) · [Tecnologías del frontend](#-tecnologías-usadas-en-la-interfaz-móvil)

### 🔌 ¿Qué es MQTT?

**MQTT** (Message Queuing Telemetry Transport) es un protocolo de mensajería ligero pensado para dispositivos con poca memoria y conexiones inestables — por eso es el estándar de facto en proyectos de **IoT** (Internet de las Cosas) como este, donde un ESP32 con pocos recursos necesita comunicarse de forma confiable.

Funciona con un modelo **publicador/suscriptor** (pub/sub), muy distinto a una petición HTTP normal:

- Nadie le "pregunta" directamente al ESP32 ni el ESP32 le pregunta directamente a tu PC.
- En cambio, ambos se conectan a un tercero llamado **broker**, y se comunican dejando y leyendo mensajes en "canales" llamados **topics**.

```
   PC (Flask / consola)                    ESP32
         │                                    │
         │  publica en                        │  está SUSCRITO a
         │  "…/comando"                        │  "…/comando"
         ▼                                    ▼
   ┌─────────────────────────────────────────────┐
   │            BROKER MQTT (intermediario)        │
   │            broker.hivemq.com                  │
   └─────────────────────────────────────────────┘
         ▲                                    │
         │  está SUSCRITO a                    │  publica en
         │  "…/estado"                          │  "…/estado"
         │                                    ▼
   PC (recibe temperatura,               (reporta lo que
   confirmaciones, etc.)                  acaba de hacer)
```

**¿Por qué usar esto en vez de que el celular hable directo con el ESP32?** Porque el ESP32 casi nunca tiene una IP pública ni fija, y exponerlo directo a internet sería inseguro. Con MQTT, ambos "salen" hacia el mismo broker (sin que nadie necesite recibir conexiones entrantes), lo cual es mucho más simple de configurar en una red doméstica o universitaria.

### 🖧 ¿Qué es un broker?

El **broker** es el servidor intermediario que recibe todos los mensajes publicados y los reparte a quien esté suscrito al topic correspondiente. En este proyecto se usa `broker.hivemq.com`, que es **público y gratuito** — cualquiera en internet puede usarlo, por eso el proyecto define un **prefijo de topic único** (`unimilitar_duchainteligente_hearvl2026`) para no mezclar sus mensajes con los de otro grupo que también esté usando ese broker.

### 🏷️ ¿Qué es un topic?

Un **topic** es simplemente el "nombre del canal" donde se publican y escuchan mensajes, como si fuera una emisora de radio. Este proyecto usa dos:

| Topic | Quién publica | Quién escucha | Ejemplo de mensaje |
|---|---|---|---|
| `.../comando` | PC (Flask o consola) | ESP32 | `"encender ducha"` |
| `.../estado` | ESP32 | PC (Flask o consola) | `"Ducha ENCENDIDA"`, `"Temp: 23.5 C \| Hum: 45.0 %"` |

### 🧠 ¿Qué es un LLM y por qué se usa Groq?

Un **LLM** (Large Language Model, o "modelo de lenguaje grande") es el tipo de inteligencia artificial detrás de cosas como ChatGPT: entiende texto en lenguaje natural y puede seguir instrucciones. Aquí se usa para traducir frases como *"quiero dormir"* al comando exacto que el ESP32 entiende (`nocturno`), gracias a un **prompt de sistema** que le explica las reglas de antemano.

**Groq** no es el modelo en sí, sino la empresa/API que lo sirve — se eligió porque ofrece esta funcionalidad de forma gratuita y con respuestas muy rápidas, ideal para que el sistema se sienta "instantáneo" al dar una orden.

### 🎙️ ¿Qué es Whisper?

**Whisper** es un modelo de IA (originalmente de OpenAI) especializado en **transcripción de voz a texto**. Groq también lo ofrece como servicio. El flujo completo cuando hablas por el micrófono del celular es:

```
Tu voz (audio) → Whisper (Groq) → texto en español → LLM (Groq) → comando → MQTT → ESP32
```

### 🔒 ¿Qué es HTTPS y por qué el "certificado no confiable"?

**HTTPS** es la versión segura (cifrada) de HTTP, el protocolo con el que los navegadores cargan páginas web. Los navegadores modernos **solo permiten usar el micrófono en páginas HTTPS** (o en `localhost`), por seguridad — así una página cualquiera no puede grabarte a escondidas.

Como este servidor corre en tu propia red local y no tiene un certificado "oficial" firmado por una autoridad reconocida (como sí tienen los bancos o Google), el navegador genera uno **autofirmado** (`ssl_context="adhoc"`) y te muestra una advertencia de "sitio no seguro". Es esperado: es tu propio servidor, en tu propia red, así que puedes darle "continuar" sin problema.

### 🔢 ¿Por qué el puerto 5000?

Cuando visitas `https://<IP-de-tu-PC>:5000`, el `:5000` es el **puerto**: la "puerta" específica de tu PC por la que las peticiones llegan al programa correcto (tu PC puede tener decenas de programas escuchando en distintos puertos a la vez).

- **5000 es el puerto por defecto de Flask** cuando no se especifica otro (Django, por ejemplo, usa el 8000).
- Los puertos del 0 al 1023 (como el 80 para HTTP o el 443 para HTTPS) son **privilegiados** y suelen requerir permisos de administrador; el 5000 está en el rango libre (1024–49151), así que cualquier usuario puede levantar ahí un servidor sin fricción.
- Es poco probable que otro programa ya esté usando ese puerto en tu PC, a diferencia del 80 o el 443.

Si quisieras cambiarlo, bastaría con modificar `port=5000` en `app.py` y usar ese mismo número en la URL desde el celular.

### 📟 ¿Qué es el ESP32 y qué hace aquí?

El **ESP32** es un microcontrolador (una "mini computadora" de bajo costo) con **WiFi integrado**, ideal para proyectos de electrónica conectada. En este sistema es el que:
- Recibe comandos por MQTT y mueve físicamente los LEDs y el servomotor
- Lee el sensor de temperatura/humedad (**DHT11**)
- Publica su estado de vuelta al broker para que el dashboard se actualice

A diferencia de tu PC o celular, el ESP32 **no corre Python** — su firmware (`DuchaInteligente.ino`) está escrito en C++ y se sube con Arduino IDE.

### 🔑 ¿Qué son las variables de entorno y por qué la API key no va en el código?

Una **variable de entorno** es un valor que vive "fuera" del código, en el sistema operativo, y que el programa lee en tiempo de ejecución con `os.environ.get("GROQ_API_KEY")`.

**¿Por qué no escribir la key directo en `bano_core.py`?** Porque ese archivo se sube a GitHub, y una API key es como una contraseña: si queda escrita en el código y el repositorio es público, cualquiera podría copiarla y usar tu cuenta de Groq (gastando tu cupo gratuito o, en un servicio de pago, generando cargos). Por eso se define aparte:

```bash
# PowerShell
$env:GROQ_API_KEY = "tu_api_key_aqui"

# CMD
set GROQ_API_KEY=tu_api_key_aqui
```

> 💡 Si en algún momento vas a subir este proyecto a GitHub, revisa que tu `.gitignore` excluya cualquier archivo `.env` que uses para guardar claves, para no subirlas por accidente.

### 🌐 ¿Qué es una API REST y qué es JSON?

Una **API** (Interfaz de Programación de Aplicaciones) es simplemente un conjunto de "puertas" (rutas/endpoints) que un programa expone para que otros programas le pidan cosas. Este proyecto usa el estilo **REST**, donde cada acción es una combinación de una **ruta** (URL) y un **método HTTP**:

| Método HTTP | Uso típico |
|---|---|
| `GET` | Pedir/leer información (ej. `/api/estado`) |
| `POST` | Enviar/crear algo (ej. enviar un comando en `/api/comando`) |

Los datos que viajan entre el navegador y Flask van en formato **JSON** (JavaScript Object Notation) — un texto estructurado en `{ "clave": "valor" }` muy fácil de leer tanto para humanos como para programas. Por ejemplo, cuando escribes un comando, el navegador envía:

```json
{ "texto": "enciende la ducha" }
```

Y Flask responde con algo como:

```json
{ "ok": true, "comandos": ["encender ducha"], "mqtt_conectado": true }
```

### 🔧 ¿Qué son los pines GPIO y el sensor DHT11?

Los **pines GPIO** (General Purpose Input/Output) son las "patitas" físicas del ESP32 que se pueden programar como entrada (leer una señal, ej. un sensor) o salida (enviar una señal, ej. encender un LED). En el código se identifican por número:

```cpp
#define LED_BLANCO_1 25   // GPIO 25 controla un LED de luz diurna
#define DHT_PIN 4         // GPIO 4 está conectado al sensor DHT11
```

El **DHT11** es un sensor económico que mide **temperatura y humedad** del ambiente y las entrega por un solo cable de datos. El ESP32 lo lee cada cierto intervalo (`leerDHT11()`) y publica el resultado por MQTT para que el dashboard lo muestre.

### 🌀 ¿Cómo funciona el servomotor de la persiana?

Un **servomotor** es un motor que, a diferencia de uno normal, no gira sin parar: se le indica un **ángulo específico** (entre 0° y 180°) y se posiciona ahí y se queda quieto. Es ideal para simular la apertura y cierre de una persiana con un movimiento mecánico simple, como una manivela.

```cpp
persiana.write(165);  // 165° = posición ABIERTA
persiana.write(75);   // 75°  = posición CERRADA
```

Estos ángulos (165° y 75°) se calibran de forma manual según cómo quede montado físicamente el servo respecto a la persiana — no son un estándar, son "lo que funcionó" para este montaje en particular. Si armas el tuyo distinto, es normal tener que ajustar estos números probando.

### ⏱️ ¿Por qué no se usa `delay()` en el ESP32? (código no bloqueante)

En Arduino, `delay(1000)` **congela por completo** el microcontrolador durante ese tiempo — no puede hacer nada más, ni siquiera revisar si llegó un mensaje MQTT. Si el ESP32 tuviera que esperar así cada vez que revisa el WiFi o el sensor, se volvería lento e insensible a comandos.

Por eso el firmware usa el patrón de **"código no bloqueante"**, comparando el tiempo transcurrido con `millis()` (el número de milisegundos desde que se encendió el ESP32) en vez de detener todo con `delay()`:

```cpp
if (millis() - ultimaLectura < INTERVALO_DHT) {
    return;  // aún no toca leer el sensor, sigue con lo demás
}
```

Así, en cada vuelta del `loop()` el ESP32 puede seguir atendiendo WiFi, MQTT y comandos por serial, sin quedarse "congelado" esperando el sensor o una reconexión.

### 🖥️ Tecnologías usadas en la interfaz móvil

El `index.html` usa varias funciones nativas del navegador (sin frameworks externos), útiles de conocer si vas a modificarlo:

| Tecnología | Para qué se usa aquí |
|---|---|
| `fetch()` | Enviar y recibir datos JSON del servidor Flask (`async/await`) |
| `MediaRecorder` | Grabar audio del micrófono mientras se mantiene presionado el botón |
| `Blob` | Empaquetar el audio grabado en un archivo para enviarlo por `FormData` |
| `SpeechSynthesisUtterance` | Hacer que el navegador **lea en voz alta** la confirmación de cada acción (Text-to-Speech) |
| `localStorage` | Recordar si el usuario dejó activada o desactivada la voz, incluso si cierra la página |
| `setInterval` | Refrescar el dashboard cada 5s y pedir sensores nuevos cada 20s automáticamente |

---

## 🏗 Arquitectura general

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

**Idea clave:** toda la lógica de conexión MQTT y de interpretación de lenguaje natural vive en un solo archivo (`bano_core.py`) para no duplicarla entre la versión de consola y la versión web. Tanto `chatbot_bano.py` como `app.py` solo se encargan de la interfaz (consola o navegador) y llaman a las funciones de `bano_core.py`.

---

## 📁 Estructura del repositorio

```
Sistema-Bano-Domotico/
├── app.py                     # Servidor Flask (control desde el celular)
├── bano_core.py                # Lógica compartida: MQTT, Groq, Whisper
├── chatbot_bano.py              # Chatbot de consola
├── DuchaInteligente.ino          # Firmware del ESP32
├── templates/
│   └── index.html                # Interfaz móvil (HTML+CSS+JS)
├── docs/
│   └── imagenes/                  # Capturas, fotos y GIFs para este README
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ✨ Características

| | |
|---|---|
| 🗣️ **Comandos por voz** | Habla en español natural ("enciende la ducha y abre la persiana") |
| ⌨️ **Comandos por texto** | Desde consola o desde el campo de texto del celular |
| 💡 **3 modos de luz** | Diurno, nocturno y sauna — mutuamente excluyentes |
| 🚿 **Control de ducha** | Encender / apagar remotamente |
| 🪟 **Persiana motorizada** | Abrir / cerrar con servomotor |
| 🌡️ **Sensores en vivo** | Temperatura y humedad (DHT11) en el dashboard |
| 🔊 **Respuesta por voz** | El navegador confirma en voz alta cada acción (Text-to-Speech) |
| 📶 **Reconexión automática** | WiFi y MQTT se reconectan solos sin bloquear el sistema |

---

## ⚙️ Requisitos

- Python 3.10+
- Una cuenta en [Groq](https://console.groq.com/) para obtener una API key gratuita (se usa para interpretar comandos y transcribir voz)
- Un ESP32 con los componentes: LEDs, sensor DHT11, micro-servo
- Arduino IDE (o PlatformIO) con las librerías: `DHT sensor library`, `ESP32Servo`, `PubSubClient`

---

## 📥 Instalación

```bash
git clone https://github.com/tu-usuario/Sistema-Bano-Domotico.git
cd Sistema-Bano-Domotico
pip install -r requirements.txt
```

Define tu API key de Groq como variable de entorno antes de correr cualquiera de los dos programas:

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
Te dará una URL tipo `https://<IP-de-tu-PC>:5000` para abrir desde el navegador del celular. El certificado será autofirmado (aparece una advertencia, es normal — es tu propio servidor).

---

## 🧩 Explicación del código, bloque por bloque

### 1. `bano_core.py` — el cerebro compartido

**Configuración MQTT**
```python
BROKER = "broker.hivemq.com"
TOPIC_PREFIJO = "unimilitar_duchainteligente_hearvl2026"
```
Se usa un broker MQTT **público**, así que se define un prefijo único de topic para no chocar con otros proyectos que usen el mismo broker. Este mismo prefijo debe coincidir exactamente con el que está en el `.ino`.

**Configuración Groq y el prompt del sistema**

Se le explica al modelo de lenguaje, en un *prompt de sistema*, cuáles son los únicos comandos válidos y cómo debe mapear frases en español ("enciende la ducha", "quiero dormir") a esos comandos exactos. También puede devolver **varios comandos separados por comas** si el usuario pide más de una acción en un solo mensaje.

**Cliente MQTT y estado del baño**

`ESTADO_ACTUAL` es un diccionario que se va actualizando cada vez que llega un mensaje del ESP32 por el topic de estado (por ejemplo, "Ducha ENCENDIDA" o "Temp: 23.50 C | Hum: 45.00 %"). La función `_actualizar_estado_desde_mensaje()` usa expresiones regulares para extraer temperatura y humedad.

**Conexión MQTT no bloqueante**

La conexión es asíncrona: si el broker tarda o falla, el programa no se congela. El hilo de red de `paho-mqtt` reintenta solo, de forma indefinida.

**Envío de comandos**

Publican el o los comandos en el topic MQTT que escucha el ESP32, con una pequeña pausa entre comandos múltiples para que el microcontrolador no reciba todo de golpe.

**Interpretación de texto con Groq**

Envía el texto del usuario a la API de Groq junto con el prompt de sistema, con reintentos automáticos (backoff exponencial) si hay error de red o el servidor está saturado (código 429 o 5xx). Al final limpia la respuesta con `_depurar_lista_comandos()`, que descarta cualquier palabra que no sea un comando válido, y si el usuario pidió dos modos de luz contradictorios en el mismo mensaje, se queda solo con el último.

**Transcripción de voz**

Envía el audio grabado (desde el navegador o el micrófono) a la API de Whisper de Groq, y devuelve el texto transcrito en español, que luego se vuelve a pasar por `interpretar_mensaje()`.

### 2. `chatbot_bano.py` — interfaz de consola

Es un loop simple: lee lo que el usuario escribe, lo pasa a `bano_core.interpretar_mensaje()`, y si se reconoce algún comando, lo envía al ESP32. Escribiendo `"salir"` termina el programa y cierra la conexión MQTT de forma ordenada.

### 3. `app.py` — servidor web (Flask)

**Detección de IP local:** truco para obtener la IP del PC en la red local sin necesitar internet real: abre un socket UDP hacia una IP externa solo para que el sistema operativo elija la interfaz de red correcta, y lee la IP desde ahí.

**Rutas principales:**

| Ruta | Método | Qué hace |
|---|---|---|
| `/` | GET | Sirve `templates/index.html` |
| `/api/comando` | POST | Recibe texto, lo interpreta con Groq y envía comandos al ESP32 |
| `/api/comando-voz` | POST | Recibe un archivo de audio, lo transcribe y luego hace lo mismo que `/api/comando` |
| `/api/estado` | GET | Devuelve el último estado conocido del baño (para el dashboard) |
| `/api/refrescar` | POST | Le pide directamente al ESP32 que reporte estado (sin pasar por Groq) |

Corre con HTTPS autofirmado (`ssl_context="adhoc"`) porque los navegadores solo permiten acceso al micrófono en páginas seguras. `host="0.0.0.0"` hace que el servidor sea visible desde otros dispositivos de la red (el celular), no solo desde el propio PC.

### 4. `templates/index.html` — interfaz móvil

Dashboard visual con tarjetas para los 3 modos de luz (mutuamente excluyentes), toggles de ducha/persiana y tarjetas de sensores (temperatura/humedad), que se repintan cada vez que llega estado nuevo. El botón de micrófono usa `MediaRecorder` para grabar mientras se mantiene presionado, y el navegador confirma cada acción en voz alta con `SpeechSynthesisUtterance`.

### 5. `DuchaInteligente.ino` — firmware del ESP32

Maneja reconexión de WiFi y MQTT no bloqueante, modos de luz mutuamente excluyentes (siempre apaga los otros antes de encender uno), la persiana con servomotor, lectura periódica del sensor DHT11, y el procesamiento de comandos recibidos tanto por MQTT como por el monitor serial (útil para pruebas sin depender del WiFi).

---

## 🎛 Comandos disponibles

| Comando | Acción |
|---|---|
| `diurno` | Enciende la iluminación diurna (luz blanca) |
| `nocturno` | Enciende la iluminación nocturna (luz tenue) |
| `sauna` | Enciende el modo sauna |
| `encender ducha` | Enciende la ducha |
| `apagar ducha` | Apaga la ducha |
| `abrir persiana` | Abre la persiana motorizada |
| `cerrar persiana` | Cierra la persiana motorizada |
| `temperatura` | Consulta la temperatura actual |
| `humedad` | Consulta la humedad actual |
| `estado` | Consulta el estado general del baño |

> 💡 También puedes combinar varios en un solo mensaje: *"enciende la ducha y abre la persiana"*.

---

## 🔒 Nota de seguridad

`broker.hivemq.com` es un broker MQTT **público y sin autenticación**. Cualquiera que conozca el prefijo de topic (`unimilitar_duchainteligente_hearvl2026`) podría enviar comandos al sistema. Para un proyecto académico de demostración esto es aceptable, pero para un uso real se recomendaría un broker privado con usuario/contraseña o TLS.

---

## 👤 Autor

Proyecto desarrollado por **Julián** — Ingeniería Mecatrónica, Universidad Militar Nueva Granada.

<div align="center">
<sub>Hecho con 🛁, ESP32 y un poco de IA</sub>
</div>
