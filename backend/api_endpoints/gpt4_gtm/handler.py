from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

gpt4_blueprint = Blueprint('gpt4', __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BrXpyWs6"

@gpt4_blueprint.route("/gtm/respond", methods=["POST"])
def generate_response_openai():
    try:
        prompt = request.json.get("prompt", "").strip()
        if not prompt:
            return jsonify({"error": "Missing prompt"}), 400

        # Call OpenAI
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a chatbot assistant for the company Anote. You should help the user to answer their question."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        import logging
        logging.error(f"An error occurred: {e}", exc_info=True)
        return jsonify({"error": "An internal error has occurred."}), 500

handler = gpt4_blueprint
