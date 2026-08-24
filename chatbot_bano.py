"""
chatbot_bano.py
Chatbot de CONSOLA para el baño inteligente.

Toda la lógica real (MQTT, interpretación con Groq, transcripción de
voz) vive en bano_core.py. Este archivo solo se encarga del loop de
consola: leer lo que escribe el usuario, mostrarlo bonito y llamar a
las funciones de bano_core.

Requiere:
    pip install paho-mqtt requests

Antes de correr, define tu API key de Groq como variable de entorno:

    PowerShell:
        $env:GROQ_API_KEY = "tu_api_key_aqui"

    CMD:
        set GROQ_API_KEY=tu_api_key_aqui

Si no defines la variable, bano_core.py te avisará claramente en vez
de fallar con un error confuso.
"""

import bano_core as core


def main():
    print("=" * 50)
    print(" CHATBOT - BAÑO INTELIGENTE (Groq + MQTT)")
    print("=" * 50)
    print()

    core.conectar_mqtt()

    print("Escribe lo que quieras (ej. 'enciende la ducha y abre la persiana')")
    print("Escribe 'salir' para terminar\n")

    try:
        while True:
            texto = input("Tú: ").strip()

            if texto.lower() == "salir":
                break

            if not texto:
                continue

            comandos = core.interpretar_mensaje(texto)

            if not comandos:
                print("Bot: No logré identificar ningún comando válido, intenta de otra forma.\n")
                continue

            print(f"Bot: Entendido -> ejecutando {comandos}\n")
            core.enviar_comandos_esp32(comandos)

    except KeyboardInterrupt:
        pass
    finally:
        core.mqtt_client.loop_stop()
        core.mqtt_client.disconnect()
        print("\nDesconectado.")


if __name__ == "__main__":
    main()