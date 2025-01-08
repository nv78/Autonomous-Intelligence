from flask import jsonify
from database.db import delete_agent

def DeleteAgentHandler(request):
    agent_id = request.json["agent_id"]
    return delete_agent(agent_id)