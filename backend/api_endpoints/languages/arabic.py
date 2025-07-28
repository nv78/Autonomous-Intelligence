from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
import sys

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

arabic_blueprint = Blueprint('arabic', __name__)

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BtL5Rskw"
LANGUAGE_KEY = "arabic"

@arabic_blueprint.route("/api/chat/arabic", methods=["POST"])
def chat_arabic():
    try:
        messages = request.json.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are built to serve people on the Anote website. You are a chatbot assistant that helps the user to answer any questions in arabic. Respond in arabic no matter the language of the user. Even if the user writes in a different language, only respond in arabic."
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
        app.logger.error("An error occurred: %s", traceback.format_exc())
        return jsonify({"error": "An internal error has occurred."}), 500