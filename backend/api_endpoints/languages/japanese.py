from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

japanese_blueprint = Blueprint('japanese', __name__)

LANGUAGE_KEY = "japanese"
MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::Bt2nGdcd"

@japanese_blueprint.route("/api/chat/japanese", methods=["POST"])
def chat_japanese():
    try:
        messages = request.json.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are built to serve people on the Anote website. You are a chatbot assistant that helps the user to answer any questions in Japanese. Respond in Japanese no matter the language of the user. Even if the user writes in a different language, only respond in Japanese."
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
        import logging
        logging.exception("An error occurred while processing the request.")
        return jsonify({"error": "An internal error has occurred"}), 500