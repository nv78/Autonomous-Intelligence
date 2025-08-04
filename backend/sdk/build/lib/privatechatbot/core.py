import requests
import json
# import time

class PrivateChatbot:
    def __init__(self, api_key):
        # self.API_BASE_URL = 'http://localhost:5000'
        self.API_BASE_URL = 'https://api.privatechatbot.ai'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

    def upload(self, task_type, model_type, ticker=None, file_paths=None):

        """Upload documents or specify a ticker for data retrieval and Q&A. This method supports various tasks, such as uploading documents or querying the government's EDGAR database.

        Args:
            task_type (str): Specifies the type of task to perform. This can be document-based interaction (e.g., "documents") or financial data analysis ("edgar").
            model_type (str): Determines the AI model to use for processing the request. Different model types available are "gpt" for GPT-4 and "claude" for Claude.
            ticker (str, optional): The ticker symbol for financial data analysis tasks. Required if the task_type is 'edgar'. Example: 'AAPL' for Apple Inc.
            file_paths (list[str], optional): A list of file paths to documents for document-based tasks. Required if task_type is 'documents'. Example: ['path/to/file1.pdf', 'path/to/file2.pdf'].

        Returns:
            response (dict): A JSON response from the API, including the `chat_id` for interactions based on the uploaded content or specified ticker.
        """

        if task_type is None:
            return {"error": "Task type is not set. Please enter a task type"}

        if model_type is None:
            return {"error": "Model type is not set. Please enter a model type"}

        if ticker is None and file_paths is None:
             return {"error": "You must enter at least one of the following: ticker or file_paths"}

        if task_type == "documents": #Question-answering
            if file_paths is None:
                return {"error": "You are attempting to do question-answering. There are no files uploaded. Please upload at least one file."}
            else:
                url = f"{self.API_BASE_URL}/public/upload"

                data = {
                    "task_type": task_type,
                    "model_type": model_type
                }

                files = []
                opened_files = []
                for path in file_paths:
                    try:
                        file = open(path, 'rb')
                        opened_files.append(file)
                        files.append(("files[]", (path.split('/')[-1], file, "application/octet-stream")))
                    except Exception as e:
                        return {"error": f"Error opening file {path}: {e}"}

                headers = {key: val for key, val in self.headers.items() if key.lower() != 'content-type'}

                try:
                    response = requests.post(url, data=data, files=files, headers=headers)
                    return response.json()
                except requests.exceptions.JSONDecodeError as e:
                    return {"error": "Failed to decode JSON response"}
                finally:
                    for file in opened_files:
                        file.close()
        elif task_type == "edgar":
            if not ticker:
                return {"error": "You are attempting to use EDGAR. There is no ticker uploaded. Please enter a ticker."}
            else:
                url = f"{self.API_BASE_URL}/public/upload"

                data = {
                    "task_type": task_type,
                    "model_type": model_type,
                    "ticker": ticker
                }

                headers = {key: val for key, val in self.headers.items() if key.lower() != 'content-type'}

                try:
                    response = requests.post(url, data=data, headers=headers)
                    return response.json()
                except requests.exceptions.JSONDecodeError as e:
                    return {"error": "Failed to decode JSON response"}
        else:
            return {"error": "Task type is not recognized. Please enter a valid task type."}


    def chat(self, chat_id, message, finetuned_model_key=None):
        """Send a message to the chatbot based on documents previously uploaded.

        Args:
            chat_id (int): The ID of the chat that has had documents uploaded.
            message (str): The message to send to the chatbot.
            finetuned_model_key (str, optional): An optional custom model OpenAI key. If provided, the chatbot uses this finetuned model for the response.

        Returns:
            response (dict): The JSON response from the API containing `answer`, `message_id` and `sources` (which contains the document name and the relevant chunk).
        """

        if not chat_id:
            return {"error": "Chat ID is not set. Please upload documents first and enter the chat ID."}

        if not message:
            return {"error": "Message is not set. Please enter a message to send."}

        url = f"{self.API_BASE_URL}/public/chat"
        data = {
            "chat_id": chat_id,
            "message": message,
            "model_key": finetuned_model_key
        }
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()

    def evaluate(self, message_id):
        """Evaluate predictions on one or multiple documents/text.

        Args:
            message_id (str): The ID of the message associated with the uploaded documents. This ID is used to identify which set of documents/text predictions should be evaluated.

        Returns:
            response (dict): A JSON response from the API, containing the evaluation results, `answer_relevancy`, `faithfulness` of the predictions on the specified message's documents or text. If the message ID is not provided or invalid, the function returns an error message indicating that a valid message ID is required for the operation.
        """

        if not message_id:
            return {"error": "Dataset ID is not set. Please create a dataset first."}

        url = f"{self.API_BASE_URL}/public/evaluate"
        # For file uploads, requests can handle files directly in the 'files' parameter

        data = {'message_id': message_id} #'task_type': task_type}  # Infer task type for now
        response = requests.post(url, json=data, headers=self.headers)
        return response.json()