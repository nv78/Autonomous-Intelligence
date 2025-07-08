from flask import Blueprint, request, jsonify
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
import os
gpt2_blueprint = Blueprint('gpt2', __name__)

model_name = "rfrey/fine_tuned_gpt2"
token = os.getenv("HUGGINGFACE") # Or use os.getenv("HF_TOKEN")

model = GPT2LMHeadModel.from_pretrained(model_name, token=token)
tokenizer = GPT2Tokenizer.from_pretrained(model_name, token=token)

@gpt2_blueprint.route("/gtm/respond", methods=["POST"])
def generate_response():
    prompt = request.json.get("prompt", "")
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=150)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return jsonify({"response": response})

handler = gpt2_blueprint
