# List Agents
::: fsdk.api.Anote.list_agents
    options:
        show_source: false

Sample usage:

``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
anote = Anote(api_key=api_key)

response = anote.list_agents()
print(response)
```
Response (JSON):

``` py
[
  {
    "agent_id": 123,
    "type": "WebSurferAgent",
    "status": "active"
  },
  {
    "agent_id": 124,
    "type": "FinanceAgent",
    "status": "idle"
  }
]
```