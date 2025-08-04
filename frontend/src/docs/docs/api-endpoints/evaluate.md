# Evaluate

::: fsdk.api.Anote.evaluate
    options:
        show_source: false


Sample usage:
``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=False) #You can select isPrivate=True if you want to use private models


message_id = 5
response = privategpt.evaluate(message_id)
```

Response is given as a JSON in this format:
``` py
{
    'answer_relevancy': 0.88,
    'faithfulness': 1.0
}
```


