
# Upload - Public

::: fsdk.api.Anote.upload
    options:
        show_source: false


Sample usage for uploading documents:
``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=False)

file_paths = ['doc1.pdf', 'doc2.pdf']

response = Anote.upload(task_type="documents", model_type="gpt", file_paths=file_paths)
```

Response is given as a JSON in this format:
``` py
{
  "id": 5
}
```

Sample usage for using Edgar:
``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=False)

response = Anote.upload(task_type="edgar", model_type="claude", ticker="aapl")
```
Response is given as a JSON in this format:
``` py
{
  "id": 5
}
```