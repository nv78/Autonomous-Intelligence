from flask import Blueprint, request, jsonify
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch

gpt2_blueprint = Blueprint('gpt2', __name__)

model_name = "rfrey/fine_tuned_gpt2"
# token = "your_hf_token_here"  # Or use os.getenv("HF_TOKEN")

model = GPT2LMHeadModel.from_pretrained(model_name)
tokenizer = GPT2Tokenizer.from_pretrained(model_name)

@gpt2_blueprint.route("/gtm/respond", methods=["POST"])
def generate_response():
    try:
        prompt = request.json.get("prompt", "")
        print(f"[DEBUG] Received prompt: {prompt}")
        
        inputs = tokenizer(prompt, return_tensors="pt")
        print("[DEBUG] Tokenized input.")

        outputs = model.generate(**inputs, max_length=150)
        print("[DEBUG] Model generated output.")

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"[DEBUG] Decoded response: {response}")

        return jsonify({"response": response})
    
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": "Internal server error"}), 500

handler = gpt2_blueprint