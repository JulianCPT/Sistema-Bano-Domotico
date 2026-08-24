"""
app.py
Servidor web para controlar el baño inteligente desde el celular.

Sirve una página móvil (templates/index.html) con:
  - Un campo de texto para escribir comandos
  - Un botón grande de micrófono (mantén presionado, habla, suelta)

Corre en HTTPS con certificado autofirmado, porque los navegadores
solo dan acceso al micrófono en páginas seguras (https o localhost).
La primera vez que abras la página desde el celular, verás una
advertencia de "certificado no confiable" — es normal, solo acepta
continuar (es tu propio servidor, en tu propia red).

Requiere:
    pip install flask pyopenssl

Correr:
    python app.py

Luego, desde el celular (conectado a la MISMA red WiFi que este PC):
    https://<IP-DE-TU-PC>:5000

Para saber la IP de tu PC en la red local:
    Windows:      ipconfig        (busca "Dirección IPv4")
    Mac/Linux:    ifconfig o ip a

CONSOLA: solo se muestran errores y una línea por cada petición
(qué se pidió -> qué comandos se ejecutaron). El resto de logs
(peticiones HTTP de Flask, mensajes internos de MQTT) están apagados.
"""

import logging
import socket

from flask import Flask, render_template, request, jsonify

import bano_core as core

# Apaga el log automático de Flask/Werkzeug (una línea por cada
# petición HTTP tipo '127.0.0.1 - - [fecha] "POST /api/comando..."').
# Solo deja pasar errores reales del servidor.
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)


def obtener_ip_local() -> str:
    """
    Obtiene la IP de este PC dentro de la red local (la misma que
    verías con ipconfig/ifconfig), sin necesidad de conexión real a
    internet: solo abre un socket UDP hacia una IP externa para que
    el sistema operativo elija la interfaz de red correcta.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/comando", methods=["POST"])
def api_comando():
    datos = request.get_json(silent=True) or {}
    texto = (datos.get("texto") or "").strip()

    if not texto:
        print("[Petición] texto vacío -> rechazado")
        return jsonify({"ok": False, "error": "Texto vacío"}), 400

    comandos = core.interpretar_mensaje(texto)
    if not comandos:
        print(f"[Petición] \"{texto}\" -> sin comando reconocido")
        return jsonify({"ok": False, "texto": texto, "error": "No se identificó ningún comando válido"})

    enviado = core.enviar_comandos_esp32(comandos)
    print(f"[Petición] \"{texto}\" -> {comandos} ({'enviado' if enviado else 'ERROR al enviar'})")

    return jsonify({
        "ok": enviado,
        "texto": texto,
        "comandos": comandos,
        "mqtt_conectado": core.esta_conectado_mqtt(),
    })


@app.route("/api/comando-voz", methods=["POST"])
def api_comando_voz():
    if "audio" not in request.files:
        print("[Petición voz] sin audio -> rechazado")
        return jsonify({"ok": False, "error": "No se recibió audio"}), 400

    archivo = request.files["audio"]
    audio_bytes = archivo.read()

    if not audio_bytes:
        print("[Petición voz] audio vacío -> rechazado")
        return jsonify({"ok": False, "error": "Audio vacío"}), 400

    texto = core.transcribir_audio(
        audio_bytes,
        nombre_archivo=archivo.filename or "audio.webm",
        mime=archivo.mimetype or "audio/webm",
    )

    if not texto:
        print("[Petición voz] no se pudo transcribir")
        return jsonify({"ok": False, "error": "No se pudo transcribir el audio"})

    comandos = core.interpretar_mensaje(texto)
    if not comandos:
        print(f"[Petición voz] \"{texto}\" -> sin comando reconocido")
        return jsonify({"ok": False, "texto": texto, "error": "No se identificó ningún comando válido"})

    enviado = core.enviar_comandos_esp32(comandos)
    print(f"[Petición voz] \"{texto}\" -> {comandos} ({'enviado' if enviado else 'ERROR al enviar'})")

    return jsonify({
        "ok": enviado,
        "texto": texto,
        "comandos": comandos,
        "mqtt_conectado": core.esta_conectado_mqtt(),
    })


@app.route("/api/estado")
def api_estado():
    return jsonify(core.obtener_estado())


@app.route("/api/refrescar", methods=["POST"])
def api_refrescar():
    """
    Le pide directamente al ESP32 (sin pasar por Groq) que reporte su
    estado actual, para refrescar temperatura/humedad en el dashboard.
    """
    enviado = core.enviar_comando_esp32("estado")
    return jsonify({"ok": enviado})


if __name__ == "__main__":
    core.conectar_mqtt()

    ip_local = obtener_ip_local()
    print("=" * 50)
    print(" BAÑO INTELIGENTE - servidor listo")
    print("=" * 50)
    print(f" Desde el celular (misma red WiFi): https://{ip_local}:5000")
    print(" (aparecerá una advertencia de certificado no confiable, es normal: acepta continuar)")
    print("=" * 50)

    # host="0.0.0.0" -> accesible desde otros dispositivos en la red, no solo este PC
    # ssl_context="adhoc" -> HTTPS autofirmado (necesario para que el celular
    #                        pueda dar permiso de micrófono)
    app.run(host="0.0.0.0", port=5000, ssl_context="adhoc", debug=False)