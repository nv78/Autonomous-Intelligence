import requests
import json
import os
import re
import csv
from handlers.public_handlers import *
from handlers.private_handlers import *

class ModelType(IntEnum):
    FTGPT = 0
    LLAMA3 = 1
    MLM = 2

def _open_files(document_files):
    files = []
    if document_files is None:
        return files
    else:
        for file_path in document_files:
            file_name = os.path.basename(file_path)
            files.append(('files[]', (file_name, open(file_path, 'rb'), 'text/plain')))
        return files

def _open_training_data(x_train_csv, y_train_csv):
    with open(x_train_csv, mode='r', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        x_train = [row[0] for row in csv_reader]

    with open(y_train_csv, mode='r', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        y_train = [row[0] for row in csv_reader]

    return x_train, y_train

def _close_files(files):
    # Close files that were opened for document paths
    for _, file_tuple in files:
        file_obj = file_tuple[1]  # Closing the file object
        file_obj.close()

class Anote:
    def __init__(self, api_key, is_private, model_id):
        self.API_BASE_URL = 'http://localhost:5000'
        #self.API_BASE_URL = 'https://api.Anote.ai'
        self.is_private = is_private
        self.model_id = model_id
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

    def train(
            self,
            model_name,
            fine_tuning_type,
            x_train_csv,
            y_train_csv,
            document_files,
            initial_model_id,
            model_type = ModelType.FTGPT
        ):
        """
        Train or Fine Tune a model via supervised, unsupervised or rlhf fine tuning

        Args:
            model_name (str): The name of the model - which is referenced in the model_ids table alongside the model_id.
            model_type (str): Model that is used to do the fine tuning - could be "FT-GPT", "Llama3" for supervised, "MLM" for unsupervised.
            fine_tuning_type (str): The type of fine tuning - could be "supervised", "unsupervised" or "rlhf"
            x_train_csv (pd.DataFrame()): training data for fine tuning (string is csv of file path)- for each row could contain question or context entries
            y_train_csv (pd.DataFrame()): training labels for fine tuning (string is csv of file path) - for each row could contain answer entries
            initial_model_id (str): if rlhf fine tuning type, can add initial unsupervised model id from pretraining step for transfer learning
            document_files (list[str], optional): A list of file paths to documents for document-based tasks for training. Example: ['path/to/file1.pdf', 'path/to/file2.pdf'].

        Returns:
            response (dict): A JSON response from the API, including the `model_id` of the trained model.
        """
        if self.is_private == False:
            url = f"{self.API_BASE_URL}/public/train"
            if fine_tuning_type == "supervised":
                x_train, y_train = _open_training_data(x_train_csv, y_train_csv)

                # Prepare the data for form submission, including both files and values
                data = {
                    "modelName": model_name,
                    "modelType": model_type,
                    "x_train": json.dumps(x_train),
                    "y_train": json.dumps(y_train),
                }

                files = _open_files(document_files)

                # Note: `data` is used for non-file form fields, `files` is used for file uploads
                response = requests.post(url, data=data, headers=self.headers, files=files)

                _close_files(files)

                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        self.model_id = response_data.get('modelId')
                        return response_data
                    except requests.exceptions.JSONDecodeError:
                        print("Failed to decode JSON response for Train Supervised")
                else:
                    print(f"Supervised fine tuning request failed with status code {response.status_code}")
                return {}

            elif fine_tuning_type == "unsupervised":
                # Prepare the data for form submission, including both files and values
                data = {
                    "modelName": model_name,
                    "modelType": model_type,
                }

                files = _open_files(document_files)
                # Note: `data` is used for non-file form fields, `files` is used for file uploads
                response = requests.post(url, data=data, headers=self.headers, files=files)

                _close_files(files)

                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        self.model_id = response_data.get('modelId')
                        return response_data
                    except requests.exceptions.JSONDecodeError:
                        print("Failed to decode JSON response for Train Unsupervised")
                else:
                    print(f"Unsupervised fine tuning request failed with status code {response.status_code}")
                return {}

            elif fine_tuning_type == "rlhf":
                x_train, y_train = _open_training_data(x_train_csv, y_train_csv)

                # Prepare the data for form submission, including both files and values
                data = {
                    "initialModelId": initial_model_id,
                    "modelName": model_name + "_" + len(x_train) + "_labels",
                    "modelType": model_type,
                    "x_train": json.dumps(x_train),
                    "y_train": json.dumps(y_train),
                }

                files = _open_files(document_files)

                # Note: `data` is used for non-file form fields, `files` is used for file uploads
                response = requests.post(url, data=data, headers=self.headers, files=files)

                _close_files(files)

                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        self.model_id = response_data.get('modelId')
                        return response_data
                    except requests.exceptions.JSONDecodeError:
                        print("Failed to decode JSON response for Train Supervised")
                else:
                    print(f"Supervised fine tuning request failed with status code {response.status_code}")
                return {}


    def predict(self, model_name, model_id, question_text, context_text=None, question_csv=None, document_files = None, model_type = ModelType.GPT):
        """Make predictions based on a fine tuned model or default model.

        Args:
            model_name (str): The name of the model - which is referenced in the model_ids table alongside the model_id.
            model_id (str): The model id that is the output of the train API call - enables fine tuned models to be called.
            question_text (str): A string that contains the question.
            context_text (str): A string that contains additional text that can be concatenated to the question, if needed.
            document_files (list[str], optional): A list of file paths to documents for document-based tasks for predictions. Example: ['path/to/file1.pdf', 'path/to/file2.pdf'].

        Returns:
            response (dict): A JSON response from the API, including the `results` of the predictions.
        """
        url = f"{self.API_BASE_URL}/public/predict"
        # Handle document files
        files = _open_files(document_files)
        # Prepare the data for form submission, including both files and values
        data = {
            "modelId": model_id,
            "modelName": model_name,
            "modelType": model_type,
            "questionText": question_text,
            "additionalText": context_text,
            "questionCSV": question_csv
        }
        response = requests.post(url, files=files, data=data, headers=self.headers)

        _close_files(files)

        if response.status_code == 200:
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                print("Failed to decode JSON response for Predict")
        else:
            print(f"Predict request failed with status code {response.status_code}")
            return {}