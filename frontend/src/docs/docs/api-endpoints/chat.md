# Chat

::: fsdk.api.Anote.chat
    options:
        show_source: false


Sample usage:
``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=False) #You can select isPrivate=True if you want to use private models

chat_id = 5
response = privategpt.chat(chat_id, "What is this paper about?", finetuned_model_key="ft:gpt-35-turbo-0613:personal:anote:8DO8V2LB")
```

Response is given as a JSON in this format:
```py
{
    'answer': 'The paper on classification performance is about utilizing few-shot and active learning to enhance artificial intelligence models.,
    'message_id': 10,
    'sources': [
        ['doc2.pdf', 'To address this, we delve into few-shot and active learning, where our goal is to improve AI models with human feedback.'],
        ['doc1.pdf', 'Improving Classification Performance With Human Feedback: \n\Label a few, we label the rest']
    ]
}
```