
from flask import jsonify
from database.db import get_api_keys

def GetAPIKeysHandler(request, user_email):
    return get_api_keys(user_email)