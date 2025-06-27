# Delete Agent
::: fsdk.api.Anote.delete_agent
    options:
        show_source: false

Sample usage:

```py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
anote = Anote(api_key=api_key)

agent_id = 123
response = anote.delete_agent(agent_id)
print(response)
Response (JSON):
```

```py
{
  "agent_id": 123,
  "status": "deleted"
}
```