from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chinese_blueprint = Blueprint('chinese', __name__)

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BskbGPbc"
LANGUAGE_KEY = "chinese"

@chinese_blueprint.route("/api/chat/chinese", methods=["POST"])
def chat_chinese():
    try:
        messages = request.json.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are built to serve people on the Anote website. You are a chatbot assistant that helps the user to answer any questions in Chinese. Respond in Chinese no matter the language of the user. Even if the user writes in a different language, only respond in Chinese."
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

        return jsonify({"error": "An internal error occurred"}), 500