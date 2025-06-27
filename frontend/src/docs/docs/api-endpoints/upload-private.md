
# Upload - Private

::: fsdk.api-private.Anote.upload
    options:
        show_source: false


Sample usage for uploading documents:
``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=True)

file_paths = ['doc1.pdf', 'doc2.pdf']

response = Anote.upload(task_type="documents", model_type="llama", file_paths=file_paths)
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
Anote = Anote(api_key, isPrivate=True)

response = Anote.upload(task_type="edgar", model_type="llama", ticker="aapl")
```
Response is given as a JSON in this format:
``` py
{
  "id": 5
}
```