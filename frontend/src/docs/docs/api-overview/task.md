# Tasks

A **Task** is a discrete assignment or job for an Agent to execute. Tasks contain a description of the work, expected output, optional input requirements, and references to tools or data.

::: fsdk.anote-sdk.Task
     <!-- options:
        show_source: false -->

### Tasks Fields
- **instructions**: The main prompt or directive (e.g., `"Summarize Q3 earnings"`).
- **files_uploaded**: File paths or IDs relevant to the Task (e.g., `["report_Q3_2023.pdf"]`).
- **examples**: Optional few-shot examples or reference data.
- **expected_output**: The form or content of the final result (e.g., `"Return a markdown summary"`).
- **agent**: The Agent to which this Task is assigned.

Example:

``` python
from anote_agents import Task

task = Task(
    instructions="Summarize the Q3 earnings from the attached PDF.",
    files_uploaded=["report_Q3_2023.pdf"],
    examples=["In Q2, we saw a 12% increase in revenue..."],
    expected_output="Short text summary with key figures.",
    agent=None
)
```

#### Examples of Task Usage
Scheduling: “Find the best meeting times with {participant_count} participants.”
Research: “Gather references on quantum computing breakthroughs since 2020.”

If using structured outputs, define output_json for validation and type safety.

Example 2:

```python
from anote_agents import Task

data_analysis_task = Task(
    description="Analyze historical sales data for the past 3 years",
    expected_output="A summary of key sales trends, plus any anomalies found.",
    human_input=False,
    agent=None  # Agent can be assigned later
)
```