# Baseline Models

To start, we evaluate baseline models on the Bizbench test dataset. There are 2 public baseline models, **GPT** and **Claude**, as well as 2 private baseline models, **Llama3** and **Mistral**.

### Loading Test Dataset
``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=False)

test_df = pd.read_csv("Bizbench.csv")
```
## Public Baseline Models

### GPT-4
```
for i, row in test_df.iterrows():
    row["gpt4_answer"], row["gpt4_chunk"] = Anote.predict(
        model_name="raw_gpt4",
        model_type="gpt-4o-mini",
        question_text=row["question"],
        context_text=row["context"]
    )

test_df[["id", "gpt4_answer"]].to_csv("raw_gpt4_submission.csv")
```
### Claude

```py
for i, row in test_df.iterrows():
    row["claude_answer"], row["claude_chunk"] = Anote.predict(
        model_name="raw_claude_opus",
        model_type="claude",
        question_text=row["question"],
        context_text=row["context"]
    )

test_df[["id", "claude_answer"]].to_csv("raw_claude_submission.csv")
```
## Private Baseline Models

### Llama3

``` py
for i, row in test_df.iterrows():
    row["llama3_answer"], row["llama3_chunk"] = Anote.predict(
        model_name="raw_llama3",
        model_type="llama3",
        question_text=row["question"],
        context_text=row["context"]
    )

test_df[["id", "llama3_answer"]].to_csv("raw_llama3_submission.csv")
```
### Mistral
``` py
for i, row in test_df.iterrows():
    row["mistral_answer"], row["mistral_chunk"] = Anote.predict(
        model_name="raw_mistral",
        model_type="mistral",
        question_text=row["question"],
        context_text=row["context"]
    )

test_df[["id", "mistral_answer"]].to_csv("raw_mistral_submission.csv")
```