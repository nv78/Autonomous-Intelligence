
# Agents

An **Agent** is an autonomous unit designed to perform tasks, make decisions, and possibly interact with other Agents. Agents can be specialized by role or configured for different goals.

::: fsdk.anote-sdk.Agent
    <!-- options:
        show_source: false -->

### Agents Fields
- **name**: Short identifier for the Agent (e.g., `"FinanceAgent"`).
- **model**: Underlying LLM (e.g., `"gpt4"`, `"gpt3.5turbo"`, `"llama"`).
- **system_prompt**: A top-level prompt or role instruction (e.g., `"You are an event planner."`).
- **task**: A default Task this Agent is responsible for (optional).
- **tools**: Names of tools the Agent can call (e.g., `"ScrapeWebsiteTool"`).
- **verbose**: If `True`, logs extra debug info.

**Example**:
```python
from anote_agents import Agent

agent = Agent(
    name="FinanceAgent",
    model="gpt4",
    system_prompt="You analyze financial data.",
    task=None,
    tools=["SerperDevTool", "ScrapeWebsiteTool"],
    verbose=True
)
```

Agents can autonomously execute tasks, leverage tools to gather information or take actions, and collaborate with other agents within a crew.

**Example 2**:

```python
from anote_agents import Agent

customer_support_agent = Agent(
    role="Customer Support Agent",
    goal="Assist users with common troubleshooting steps",
    tools=[],
    verbose=True,
    backstory="You are friendly and patient, helping customers find solutions."
)
```
By defining Agents carefully, you ensure they remain focused on their intended purpose and handle tasks efficiently.