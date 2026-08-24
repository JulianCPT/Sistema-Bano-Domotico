"""
bano_core.py
Lógica compartida del baño inteligente: conexión MQTT, interpretación
de lenguaje natural con Groq (texto) y transcripción de voz (Whisper).

Tanto chatbot_bano.py (consola) como app.py (servidor web para el
celular) importan de aquí, para no duplicar la lógica en dos lados.

CONSOLA: este módulo solo imprime errores reales (fallos de conexión,
API key inválida, etc.). Los mensajes rutinarios (cada intento de
conexión, cada mensaje MQTT recibido) no se muestran para no llenar
la terminal; quien quiera ver qué acción se ejecutó en cada petición
lo ve desde app.py o chatbot_bano.py, que sí imprimen eso.
"""

import os
import re
import time
import requests
import paho.mqtt.client as mqtt

# =====================================================
# CONFIGURACIÓN MQTT
# =====================================================

BROKER = "broker.hivemq.com"
PUERTO = 1883

# Prefijo único del proyecto. broker.hivemq.com es PÚBLICO y lo usan miles
# de personas: un topic genérico como "duchainteligente/comando" puede
# chocar con el de alguien más. Debe ser EXACTAMENTE el mismo prefijo
# que el que pusiste en el .ino del ESP32.
TOPIC_PREFIJO = "unimilitar_duchainteligente_hearvl2026"
TOPIC_COMANDO = f"{TOPIC_PREFIJO}/comando"
TOPIC_ESTADO = f"{TOPIC_PREFIJO}/estado"

SEGUNDOS_ESPERA_CONEXION_INICIAL = 8
SEGUNDOS_ENTRE_COMANDOS = 0.2

# =====================================================
# CONFIGURACIÓN GROQ
# =====================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELO = "openai/gpt-oss-120b"
GROQ_TRANSCRIPCION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODELO_VOZ = "whisper-large-v3-turbo"

GROQ_MAX_REINTENTOS = 3
GROQ_ESPERA_BASE_SEGUNDOS = 1.5  # backoff exponencial: 1.5s, 3s, 6s...

COMANDOS_VALIDOS = [
    "diurno",
    "nocturno",
    "sauna",
    "encender ducha",
    "apagar ducha",
    "abrir persiana",
    "cerrar persiana",
    "temperatura",
    "humedad",
    "estado",
]

# Modos de iluminación mutuamente excluyentes: el ESP32 apaga todas las
# luces ambientales antes de encender cualquiera de ellos, así que solo
# el ÚLTIMO que se envíe queda realmente activo.
MODOS_ILUMINACION_EXCLUYENTES = {"diurno", "nocturno", "sauna"}

PROMPT_SISTEMA = f"""Eres un intérprete de comandos para un baño inteligente.
Tu única tarea es leer lo que dice el usuario y devolver uno o más de
estos comandos, SEPARADOS POR COMAS, en el orden en que deben ejecutarse,
sin explicación, sin comillas, sin numeración, sin puntuación extra:

{", ".join(COMANDOS_VALIDOS)}

El usuario puede pedir VARIAS acciones en un solo mensaje (ej. "enciende
la ducha y abre la persiana"). En ese caso devuelve cada comando separado
por una coma, ej: "encender ducha, abrir persiana"

Reglas de mapeo:
- Si el usuario pide encender luces de día, luz blanca, o dice que quiere
  claridad -> "diurno"
- Si pide modo noche, luz tenue, o dice que va a dormir -> "nocturno"
- Si menciona sauna o vapor -> "sauna"
- Si pide prender/abrir/encender la ducha -> "encender ducha"
- Si pide apagar/cerrar la ducha -> "apagar ducha"
- Si pide abrir la persiana, ventana o cortina -> "abrir persiana"
- Si pide cerrar la persiana, ventana o cortina -> "cerrar persiana"
- Si pregunta por la temperatura -> "temperatura"
- Si pregunta por la humedad -> "humedad"
- Si pregunta por el estado general del baño -> "estado"

Regla importante sobre iluminación:
"diurno", "nocturno" y "sauna" son modos de luz EXCLUYENTES entre sí
(no pueden estar encendidos al mismo tiempo). Si el usuario pide dos
modos de luz contradictorios en el mismo mensaje, incluye solo el
que el usuario quiere que quede activo AL FINAL (el más reciente en
su frase), no ambos.

Si el mensaje no corresponde a ningún comando reconocible, responde
exactamente: ninguno

Responde SOLO con la lista de comandos separados por comas, nada más."""


# =====================================================
# CLIENTE MQTT
# =====================================================

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_conectado = False

# Último estado conocido del baño, reconstruido a partir de los mensajes
# que el ESP32 publica en TOPIC_ESTADO (ej. "Modo DIURNO activado",
# "Ducha ENCENDIDA", "Temp: 23.50 C | Hum: 45.00 %"). Lo usa app.py para
# mostrar un dashboard en vez de un simple historial de texto.
ESTADO_ACTUAL = {
    "luz": None,          # "diurno" | "nocturno" | "sauna" | None
    "ducha": None,        # True | False | None
    "persiana": None,     # "abierta" | "cerrada" | None
    "temperatura": None,  # float | None
    "humedad": None,      # float | None
}


def _actualizar_estado_desde_mensaje(mensaje: str):
    m = mensaje.lower()

    if "modo diurno" in m:
        ESTADO_ACTUAL["luz"] = "diurno"
    elif "modo nocturno" in m:
        ESTADO_ACTUAL["luz"] = "nocturno"
    elif "modo sauna" in m:
        ESTADO_ACTUAL["luz"] = "sauna"

    if "ducha encendida" in m:
        ESTADO_ACTUAL["ducha"] = True
    elif "ducha apagada" in m:
        ESTADO_ACTUAL["ducha"] = False

    if "persiana abierta" in m:
        ESTADO_ACTUAL["persiana"] = "abierta"
    elif "persiana cerrada" in m:
        ESTADO_ACTUAL["persiana"] = "cerrada"

    match_temp = re.search(r"temp[^:]*:\s*(-?\d+(?:\.\d+)?)", m)
    if match_temp:
        ESTADO_ACTUAL["temperatura"] = float(match_temp.group(1))

    match_hum = re.search(r"hum[^:]*:\s*(-?\d+(?:\.\d+)?)", m)
    if match_hum:
        ESTADO_ACTUAL["humedad"] = float(match_hum.group(1))


def obtener_estado() -> dict:
    """Devuelve el último estado conocido del baño + si hay conexión MQTT."""
    return {**ESTADO_ACTUAL, "mqtt_conectado": mqtt_conectado}


def al_conectar(client, userdata, flags, reason_code, properties=None):
    global mqtt_conectado
    if reason_code == 0:
        mqtt_conectado = True
        client.subscribe(TOPIC_ESTADO)
    else:
        mqtt_conectado = False
        print(f"[ERROR MQTT] No se pudo conectar al broker (código {reason_code})")


def al_desconectar(client, userdata, flags, reason_code, properties=None):
    global mqtt_conectado
    mqtt_conectado = False


def al_recibir_mensaje(client, userdata, msg):
    texto = msg.payload.decode()
    _actualizar_estado_desde_mensaje(texto)


mqtt_client.on_connect = al_conectar
mqtt_client.on_disconnect = al_desconectar
mqtt_client.on_message = al_recibir_mensaje
mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)


def esta_conectado_mqtt() -> bool:
    return mqtt_conectado


def conectar_mqtt():
    """
    Conexión asíncrona: no bloquea ni lanza excepción si el broker
    tarda o falla en el primer intento. El hilo de red reintenta solo,
    indefinidamente, tanto en la conexión inicial como en reconexiones.
    """
    mqtt_client.connect_async(BROKER, PUERTO, keepalive=60)
    mqtt_client.loop_start()

    espera = 0.0
    while not mqtt_conectado and espera < SEGUNDOS_ESPERA_CONEXION_INICIAL:
        time.sleep(0.5)
        espera += 0.5

    if not mqtt_conectado:
        print(
            f"[ERROR MQTT] Aún no conecta después de {SEGUNDOS_ESPERA_CONEXION_INICIAL}s. "
            "Seguirá intentando en segundo plano."
        )


def enviar_comando_esp32(comando: str):
    if not mqtt_conectado:
        print(f"[ERROR MQTT] Sin conexión con el broker, no se pudo enviar '{comando}'")
        return False

    resultado = mqtt_client.publish(TOPIC_COMANDO, comando)

    if resultado.rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"[ERROR MQTT] No se pudo encolar '{comando}' (rc={resultado.rc})")
        return False
    return True


def enviar_comandos_esp32(comandos: list[str]) -> bool:
    """Envía varios comandos en secuencia con una pequeña pausa entre cada uno."""
    exito = True
    for i, comando in enumerate(comandos):
        if not enviar_comando_esp32(comando):
            exito = False
        if i < len(comandos) - 1:
            time.sleep(SEGUNDOS_ENTRE_COMANDOS)
    return exito


# =====================================================
# INTERPRETACIÓN DE TEXTO CON GROQ
# =====================================================

def _depurar_lista_comandos(comandos: list[str]) -> list[str]:
    limpios = []
    for c in comandos:
        c = c.strip().lower()
        if c in COMANDOS_VALIDOS and c not in limpios:
            limpios.append(c)

    modos_presentes = [c for c in limpios if c in MODOS_ILUMINACION_EXCLUYENTES]
    if len(modos_presentes) > 1:
        ultimo_modo = modos_presentes[-1]
        limpios = [
            c for c in limpios
            if c not in MODOS_ILUMINACION_EXCLUYENTES or c == ultimo_modo
        ]

    return limpios


def interpretar_mensaje(texto_usuario: str) -> list[str] | None:
    """Devuelve la lista de comandos detectados, o None si no se pudo interpretar."""

    if not GROQ_API_KEY:
        print("[ERROR] No se encontró la variable de entorno GROQ_API_KEY.")
        return None

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODELO,
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": texto_usuario},
        ],
        "temperature": 0,
        "max_tokens": 200,
        "reasoning_effort": "low",
    }

    ultimo_error = None

    for intento in range(1, GROQ_MAX_REINTENTOS + 1):
        try:
            respuesta = requests.post(GROQ_URL, headers=headers, json=body, timeout=15)
        except requests.exceptions.Timeout:
            ultimo_error = "timeout"
        except requests.exceptions.RequestException as e:
            ultimo_error = str(e)
        else:
            if respuesta.status_code == 401:
                print("[ERROR Groq] API key inválida (401)")
                return None

            if respuesta.status_code == 200:
                data = respuesta.json()
                try:
                    contenido = data["choices"][0]["message"]["content"].strip().lower()
                except (KeyError, IndexError):
                    print(f"[ERROR Groq] Respuesta inesperada: {data}")
                    return None

                if contenido == "ninguno":
                    return None

                comandos = _depurar_lista_comandos(contenido.split(","))
                if not comandos:
                    return None

                return comandos

            elif respuesta.status_code == 429 or respuesta.status_code >= 500:
                ultimo_error = f"HTTP {respuesta.status_code}"
            else:
                print(f"[ERROR Groq {respuesta.status_code}] {respuesta.text}")
                return None

        if intento < GROQ_MAX_REINTENTOS:
            time.sleep(GROQ_ESPERA_BASE_SEGUNDOS * (2 ** (intento - 1)))

    print(f"[ERROR Groq] No se pudo contactar después de {GROQ_MAX_REINTENTOS} intentos ({ultimo_error})")
    return None


# =====================================================
# TRANSCRIPCIÓN DE VOZ (Whisper de Groq)
# =====================================================

def transcribir_audio(audio_bytes: bytes, nombre_archivo: str = "audio.wav", mime: str = "audio/wav") -> str | None:
    """
    Envía audio a la API de transcripción de Groq (Whisper).
    Acepta wav, webm, ogg, mp3, m4a, etc. — lo que grabe el navegador
    o el micrófono del cliente que esté llamando esta función.
    """
    if not GROQ_API_KEY:
        print("[ERROR] No se encontró la variable de entorno GROQ_API_KEY.")
        return None

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    files = {"file": (nombre_archivo, audio_bytes, mime)}
    data = {"model": GROQ_MODELO_VOZ, "language": "es", "response_format": "text"}

    try:
        r = requests.post(GROQ_TRANSCRIPCION_URL, headers=headers, files=files, data=data, timeout=20)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR Voz] Error de red al transcribir: {e}")
        return None

    if r.status_code == 401:
        print("[ERROR Voz] API key inválida (401)")
        return None

    if r.status_code != 200:
        print(f"[ERROR Voz {r.status_code}] {r.text}")
        return None

    return r.text.strip()
