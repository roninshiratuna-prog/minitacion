
import os
import json
import base64
import binascii
import secrets

from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Limitar tamaño de las peticiones
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

# Credenciales guardadas en el servidor
API_KEY = os.environ.get("OPENAI_API_KEY")
SECRETO_ESP32 = os.environ.get("ESP32_TOKEN")

if not API_KEY or not SECRETO_ESP32:
    raise RuntimeError("Faltan las credenciales del servidor")

client = OpenAI(api_key=API_KEY)

SYSTEM_PROMPT = """
Eres una chica robot.

Devuelve exclusivamente un objeto JSON con:
{
    "modo_sueno": false,
    "servos": [90, 90, 90, 90, 90, 90, 90, 90,
               90, 90, 90, 90, 90, 90, 90, 90],
    "texto_respuesta": "¡Hola! Ya estoy funcionando."
}

Reglas:
- modo_sueno debe ser booleano.
- servos debe contener exactamente 16 enteros.
- Cada servo debe estar entre 0 y 180.
- Si no tienes información suficiente, conserva
  los valores neutrales de los servos.

"""

@app.route("/", methods=["GET"])
def home():
    return "Acceso denegado", 403


@app.route("/interactuar", methods=["POST"])
def interactuar():

    # Autenticación
    token = request.headers.get("Authorization", "")

    if not secrets.compare_digest(
        token,
        f"Bearer {SECRETO_ESP32}"
    ):
        return jsonify({"error": "No autorizado"}), 401

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "JSON inválido"}), 400

        texto_usuario = data.get("texto", "Hola")
        imagen_base64 = data.get("imagen", "")

        if not isinstance(texto_usuario, str):
            return jsonify({"error": "Texto inválido"}), 400

        if len(texto_usuario) > 2000:
            return jsonify({"error": "Texto demasiado largo"}), 400

        if not isinstance(imagen_base64, str):
            return jsonify({"error": "Imagen inválida"}), 400

        user_content = [
            {
                "type": "text",
                "text": texto_usuario
            }
        ]

        # Procesamiento de imagen
        if imagen_base64:

            if len(imagen_base64) > 1400000:
                return jsonify({"error": "Imagen demasiado grande"}), 413

            try:
                base64.b64decode(
                    imagen_base64,
                    validate=True
                )
            except (ValueError, binascii.Error):
                return jsonify({"error": "Base64 inválido"}), 400

            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": (
                        "data:image/jpeg;base64,"
                        + imagen_base64
                    ),
                    "detail": "low"
                }
            })

        # Solicitud a OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            response_format={
                "type": "json_object"
            },
            max_completion_tokens=300
        )

        contenido = response.choices[0].message.content

        if not contenido:
            return jsonify({"error": "Respuesta vacía"}), 502

        resultado = json.loads(contenido)

        # Validar estructura
        if not isinstance(resultado, dict):
            raise ValueError("Objeto inválido")

        servos = resultado.get("servos")
        modo_sueno = resultado.get("modo_sueno")
        texto_respuesta = resultado.get("texto_respuesta")

        if type(modo_sueno) is not bool:
            raise ValueError("modo_sueno inválido")

        if not isinstance(servos, list) or len(servos) != 16:
            raise ValueError("Cantidad de servos incorrecta")

        if any(
            type(v) is not int or not 0 <= v <= 180
            for v in servos
        ):
            raise ValueError("Valores de servos inválidos")

        if not isinstance(texto_respuesta, str):
            raise ValueError("Texto de respuesta inválido")

        if len(texto_respuesta) > 300:
            raise ValueError("Respuesta demasiado larga")

        # Respuesta JSON real para el ESP32
        return jsonify({
            "status": "ok",
            "resultado": {
                "modo_sueno": modo_sueno,
                "servos": servos,
                "texto_respuesta": texto_respuesta
            }
        }), 200

    except Exception as e:
        app.logger.exception("Error al procesar petición")
        return jsonify({
            "status": "error",
            "mensaje": "Error interno del servidor"
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
