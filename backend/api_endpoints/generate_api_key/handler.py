
from flask import jsonify
from database.db import generate_api_key

def GenerateAPIKeyHandler(request, user_email):
    return generate_api_key(user_email)