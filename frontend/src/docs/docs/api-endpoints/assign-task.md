# Assign Task
::: fsdk.api.Anote.assign_task
    options:
        show_source: false

Sample usage:

```py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
anote = Anote(api_key=api_key)

task_request = {
  "agent_id": 123,
  "description": "Research the latest data on housing prices in San Francisco."
}

response = anote.assign_task(task_request)
print(response)
```
Response (JSON):

```py
{
  "task_id": 456,
  "agent_id": 123,
  "description": "Research the latest data on housing prices in San Francisco.",
  "status": "assigned"
}
```