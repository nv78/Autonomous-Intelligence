
# Example 2: Defining Tasks

Tasks detail what the Agent should do and what output is expected.

```python
from anote_agents import Task

fetch_inventory_task = Task(
    description="Fetch current inventory from the warehouse database",
    expected_output="A JSON object with product stock levels",
    human_input=False,
    agent=None
)

print(fetch_inventory_task.description)
```