from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
import sys

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

arabic_blueprint = Blueprint('arabic', __name__)

MODEL_NAME = "gpt-3.5-turbo"

@arabic_blueprint.route("/api/chat/arabic", methods=["POST"])
def chat_arabic():
    try:
        messages = request.json.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are a chatbot assistant meant to speak to the user in arabic. You should help to user to answer on any questions in arabic. Respond in arabic no matter the language of the user."
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
        return jsonify({"error": str(e)}), 500