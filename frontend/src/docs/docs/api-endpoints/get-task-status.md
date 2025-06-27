# Get Task Status
::: fsdk.api.Anote.get_task_status
    options:
      show_source: false

Sample usage:

``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
anote = Anote(api_key=api_key)

task_id = 456
response = anote.get_task_status(task_id)
print(response)
```
Response (JSON):

``` py
{
  "task_id": 456,
  "status": "in_progress",
  "progress_details": {
    "current_step": 2,
    "total_steps": 5
  },
  "result": null
}
```