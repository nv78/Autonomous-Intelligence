
# Chatting With Predefined Agents

Here we show how to initialize and communicate with an Agent that’s already set up for a specific purpose.

```python
from anote_agents import Agent, Chat

# Predefined Agent (e.g., loaded from a config file or database)
predefined_agent = Agent(
    name="KnowledgeBaseAgent",
    role="Knowledge Base Assistant",
    goal="Answer technical questions from the internal knowledge base"
)

# Create a chat session
chat_id = Chat.create_session(agent=predefined_agent)

# Example query
user_question = "What is the recommended fix for error code 502?"
response = Chat.send_message(chat_id, user_question)

print("Agent answer:", response.answer)
print("Sources:", response.sources)
