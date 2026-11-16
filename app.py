import os
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Contraseña secreta para que solo tu ESP32 pueda entrar
SECRETO_ESP32 = "minitaaaa"

@app.route("/", methods=["GET"])
def home():
    return "Acceso denegado", 403

@app.route("/interactuar", methods=["POST"])
def interactuar():
    # Verificar que la petición lleve la contraseña correcta en las cabeceras
    token = request.headers.get("Authorization")
    if token != f"Bearer {SECRETO_ESP32}":
        return jsonify({"error": "No autorizado"}), 401

    try:
        data = request.json
        imagen_base64 = data.get("imagen", "")
        texto_usuario = data.get("texto", "Hola")

        system_prompt = (
            "Eres una chica robot autónoma. "
            "Devuelve estrictamente un objeto JSON con: "
            "1. 'modo_sueno' (booleano true/false), "
            "2. 'servos' (array exacto de 16 enteros de 0 a 180), "
            "3. 'texto_respuesta' (lo que dirás de forma breve y natural con voz de tonada)."
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        user_content = [{"type": "text", "text": texto_usuario}]
        if imagen_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{imagen_base64}"}
            })
            
        messages.append({"role": "user", "content": user_content})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"}
        )

        respuesta_ia = response.choices[0].message.content
        return jsonify({"status": "ok", "resultado": respuesta_ia}), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
