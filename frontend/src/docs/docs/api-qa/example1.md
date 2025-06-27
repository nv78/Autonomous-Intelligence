# Example 1: Defining Agents

Below is a concise example illustrating how to create an Agent with a specific role and goal.

```python
from anote_agents import Agent

support_bot = Agent(
    name="SupportBot",
    role="Technical Support",
    goal="Provide troubleshooting steps for user-reported issues",
    instructions=["Keep answers concise", "Include references where possible"],
    verbose=True
)

print(support_bot.role)
print(support_bot.goal)
```