from flask import Blueprint, request, jsonify, session
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

japanese_blueprint = Blueprint('japanese', __name__)

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BskbGPbc"
LANGUAGE_KEY = "japanese"

@japanese_blueprint.route("/api/chat/japanese", methods=["POST"])
def chat_japanese():
    try:
        # Expect messages to be a list from frontend
        incoming_messages = request.json.get("messages")
        if not incoming_messages or not isinstance(incoming_messages, list):
            return jsonify({"error": "Missing or invalid messages list"}), 400

        current_language = LANGUAGE_KEY
        previous_language = session.get("active_language")

        # If the user has switched to a new language, clear history
        if previous_language != current_language:
            session["messages"] = []
            session["active_language"] = current_language

        SYSTEM_MSG = {
            "role": "system",
            "content": "You are a chatbot assistant meant to speak to the user in Japanese. Always respond in Japanese no matter what language the user uses."
        }

        # Load or initialize conversation history
        messages = session.get("messages", [])
        if not messages:
            messages = [SYSTEM_MSG]

        # Append the new user messages
        for msg in incoming_messages:
            if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
                messages.append(msg)

        # Call OpenAI
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages
        )

        reply = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        session["messages"] = messages

        return jsonify({
            "response": reply,
            "conversation": messages
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
