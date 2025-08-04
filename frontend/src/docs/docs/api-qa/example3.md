
# Example 3: Building Teams of Agents

Sometimes multiple Agents need to work together. Here’s how you form a Crew.

```python
from anote_agents import Agent, Crew, Task

agent_web = Agent(name="WebAgent", role="Research Data")
agent_fin = Agent(name="FinanceAgent", role="Analyze Market Trends")

task_research = Task(description="Research best stocks for Q4", agent=agent_web)
task_analysis = Task(description="Perform financial analysis on the data", agent=agent_fin)

analysis_crew = Crew(
    agents=[agent_web, agent_fin],
    tasks=[task_research, task_analysis],
    verbose=True
)

results = analysis_crew.kickoff(inputs={"sector": "Technology"})
print(results)
```