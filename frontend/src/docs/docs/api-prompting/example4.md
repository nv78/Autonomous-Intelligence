# Unsupervised Fine Tuning

Doing unsupervised learning to train a Masked Language Model (MLM) on financial documents, specifically 10-K filings from the SEC Edgar database, can enhance the model's understanding of financial terminology and contexts. Unsupervised fine-tuning allows the model to learn from a large corpus of unlabelled financial documents, improving its ability to understand and generate text related to financial topics.

### Data Preparation:

Collect URLs and file paths of 10-K filings. Example sources include the SEC Edgar website and local storage for PDF files.

### Continual Pre-Training:

Unsupervised fine tuning leverages continual pre-training, which involves updating a pre-trained language model by training it incrementally on new, domain-specific data without forgetting previously learned information.

``` py
from anoteai import Anote

api_key = 'INSERT_API_KEY_HERE'
Anote = Anote(api_key, isPrivate=False)

file_paths = [
    'https://www.sec.gov/Archives/edgar/data/320193/000032019318000145/a10-k20189292018.htm',
    'https://www.sec.gov/Archives/edgar/data/320193/000119312514383437/d783162d10k.htm',
    '10-Ks/aapl-10-k.pdf', '10-Ks/amzn-20221231.pdf', '10-Ks/bankofamerica-10K.pdf',
    '10-Ks/dbx-20221231.pdf', '10-Ks/google-10-k.pdf,', '10-Ks/msft-10k_20200630.pdf', '10-Ks/nflx-20221231.pdf',
    '10-Ks/nvda-10-k.pdf', '10-Ks/path-20230131.pdf', '10-Ks/sstk-20221231.pdf'
]

fine_tune_model_id = Anote.train(
    model_name="fine_tuned_mlm_on_10ks",
    model_type="MLM",
    fine_tuning_type="unsupervised",
    document_files=file_paths
)['id']
```
### Using the Fine-Tuned Model
Once the model is fine-tuned, it can be used to perform specific NLP tasks such as answering questions or generating text based on the financial context.

``` py
import pandas as pd
test_df = pd.read_csv("Bizbench.csv")

# Fine Tuned Masked Language Model
for i, row in test_df.iterrows():
    row["ft_mlm_answer"], row["ft_mlm_chunk"] = Anote.predict(
        model_name="fine_tuned_mlm",
        model_id=fine_tuned_model_id,
        question_text=row["question"],
        context_text=row["context"]
    )

test_df[["id", "ft_mlm_answer"]].to_csv("ft_mlm_submission.csv")
```

### Additional Resources

- [Continual Learning of Natural Language Processing Tasks: A Survey](https://arxiv.org/abs/2211.12701)
- [Contrinual Pre-training of Language Models](https://arxiv.org/pdf/2302.03241)
- [Using Hugging Face transformers for MLM](https://github.com/huggingface/transformers/blob/main/examples/pytorch/language-modeling/run_mlm.py)
- [Continual Pretraining Example](https://github.com/ZixuanKe/PyContinual/blob/main/examples/continual_finetune.ipynb)
- [Fine-tuning a Pre-trained LLM with an Unlabelled Dataset](https://pradeepundefned.medium.com/fine-tuning-a-pre-trained-llm-with-unlabelled-dataset-73aa5082a5ef)