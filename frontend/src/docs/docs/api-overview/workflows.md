# Workflows

Workflows dictate how Tasks are executed within a Crew. They define the order, logic, and decision-making structure.

::: fsdk.anote-sdk.Workflow
    <!-- options:
        show_source: false -->

**Description:** Workflows define how Tasks are executed within a Crew. Common patterns include:

### Workflows Fields
- **workflow_type**: e.g., `"sequential"`, `"hierarchical"`, or `"parallel"`.
- **manager_agent**: Used in hierarchical workflows (Agent object, optional).
- **allow_parallel**: If `True`, tasks may run concurrently.

Example:

```python
workflow_example = {
    "workflow_type": "sequential",
    "manager_agent": None,
    "allow_parallel": False
}
```
## 1. Common Workflow Types

1. **Sequential**: Tasks run one after another in a predefined order. Good for simple, linear processes.

2. **Hierarchical**: Involves a "manager" agent that oversees or delegates Tasks to subordinate agents. Useful when tasks must be dynamically created or delegated.

3. **Consensual** (Planned): Focuses on collaborative decision-making among agents. Agents vote or debate to reach a consensus.


Example 2:
```python
crew = Crew(
    agents=[manager_agent, worker_agent],
    tasks=[task1, task2],
    verbose=True
)

# For hierarchical, specify a manager agent with special logic
crew.workflow_type = "hierarchical"
```