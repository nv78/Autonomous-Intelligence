from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

spanish_blueprint = Blueprint('spanish', __name__)

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BtJIlsUg"
LANGUAGE_KEY = "spanish"

@spanish_blueprint.route("/api/chat/spanish", methods=["POST"])
def chat_spanish():
    print("Received request:", request.json)  # or use logging
    try:
        messages = request.json.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are built to serve people on the Anote website. You are a chatbot assistant that helps the user to answer any questions in Spanish. Respond in Spanish no matter the language of the user. Even if the user writes in a different language, only respond in Spanish."
        }
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, SYSTEM_MSG)

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages
        )

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal error has occurred. Please try again later."}), 500