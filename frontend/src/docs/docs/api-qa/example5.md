# Example 5: Building Agentic Workflows

Demonstrates a multi-step process using multiple Agents and tasks.

```python
from anote_agents import Agent, Task, Crew

agent_planner = Agent(role="Planner", goal="Outline the steps for an event")
agent_executor = Agent(role="Executor", goal="Carry out the planned steps")

plan_task = Task(
    description="Create an event plan with {num_sessions} sessions",
    agent=agent_planner
)

execute_task = Task(
    description="Execute the event plan and provide final summary",
    agent=agent_executor
)

workflow_crew = Crew(
    agents=[agent_planner, agent_executor],
    tasks=[plan_task, execute_task],
    verbose=True
)

# Kick off
inputs = {"num_sessions": 3}
results = workflow_crew.kickoff(inputs=inputs)
print(results)
```