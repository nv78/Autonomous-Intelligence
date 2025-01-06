### LOGIC of creating the agent
from database.db import create_agent

def CreateAgentHandler(request):
    agent = request.json["agent_id"]

    agentObjs = create_agent(agent["agent_id"])
    return {
        'status': 'OK',
        'agentId': agent,
        'agent': agentObjs
    }