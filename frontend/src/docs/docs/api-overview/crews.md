# Crews

A **Crew** is a group of Agents executing one or more Tasks in a coordinated manner.

::: fsdk.anote-sdk.Crew
    <!-- options:
        show_source: false -->

### Crews Fields
- **agents**: All the Agents that will collaborate (list of Agent objects).
- **tasks**: The tasks to be completed by these Agents (list of Task objects).
- **verbose**: If `True`, logs more details during execution.

Example:

```python
from anote_agents import Crew

crew = Crew(
    agents=[venue_coordinator, logistics_manager],
    tasks=[venue_task, logistics_task],
    verbose=True
)
```

### Composition

Crews can be composed of:
- Multiple **Agents** (e.g., marketing agent, finance agent, research agent)
- One or more **Tasks** (e.g., "Conduct market research," "Prepare financial analysis")

### Execution Flow
Initialization: The Crew binds each Task to the correct Agent.
kickoff: Passes input data (if any) into tasks that contain placeholders.
Orchestration: Tasks may run sequentially or in parallel, depending on workflow.
Results: The Crew collects outputs from each Task.

Example 2:

```python
from anote_agents import Crew

team_crew = Crew(
    agents=[marketing_agent, finance_agent],
    tasks=[research_task, analysis_task],
    verbose=True
)

# Kick off the tasks
results = team_crew.kickoff(inputs={"industry": "Renewable Energy"})
```

#### Key Benefits
- Centralized management for complex multi-agent workflows.
- Clear separation of responsibilities among Agents.
- Reusability of Agents and Tasks across different Crews if desired.