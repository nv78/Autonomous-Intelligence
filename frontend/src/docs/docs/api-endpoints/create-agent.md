Create Agent
::: fsdk.api.Anote.create_agent
    options:
        show_source: false

Sample usage:

```py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
anote = Anote(api_key=api_key)

request_body = {
  "type": "WebSurferAgent",
  "config": {
    "search_criteria": {
      "role": "Data Scientist",
      "location": "San Francisco"
    }
  }
}

response = anote.create_agent(request_body)
print(response)
```
Response (JSON):

```py
{
  "agent_id": 123,
  "status": "created",
  "type": "WebSurferAgent",
  "config": {
    "search_criteria": {
      "role": "Data Scientist",
      "location": "San Francisco"
    }
  }
}
```