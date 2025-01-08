from flask import jsonify
from database.db import list_agents

def ListAgentsHandler():
    agents = list_agents()
    return jsonify(agents)