from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

korean_blueprint = Blueprint('korean', __name__)


LANGUAGE_KEY = "korean"
MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BthVmuUX"


@korean_blueprint.route("/api/chat/korean", methods=["POST"])
def chat_korean():
    try:
        messages = request.json.get("messages")
        if not messages or not isinstance(messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are a chatbot assistant meant to speak to the user in korean. You should help to user to answer on any questions in korean. Respond in korean no matter the language of the user."
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
        error_details = traceback.format_exc()
        # Log the stack trace for debugging purposes
        print(error_details)  # You may replace this with an actual logging mechanism
        # Return a generic error message to the client
        return jsonify({"error": "An internal error has occurred"}), 500