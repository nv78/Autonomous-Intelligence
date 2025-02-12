import requests
import json
import os
import re
import csv
import sys
# from handlers.public_handlers import *
# from handlers.private_handlers import *
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../api_endpoints/agents/")))
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from google.auth.transport.requests import Request

#from api_endpoints.agents.handler import CalendarAgent, WeatherAgent
from api_endpoints.agents.handler import CalendarAgent, WeatherAgent
import api_endpoints.agents.handler as handler_ai_agents

#from handler import CalendarAgent, WeatherAgent
from google.oauth2.credentials import Credentials
from flask import session, jsonify



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

class PrivateChatbot:
    def __init__(self, api_key, is_private, model_id):
        self.API_BASE_URL = 'http://localhost:5000'
        #self.API_BASE_URL = 'https://api.privatechatbot.ai'
        self.is_private = is_private
        self.model_id = model_id
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

        if self.is_private == False:
            if model_type != "gpt" and model_type != "claude":
                return {"error": "Model type is not valid. Please enter a valid model type"}
            return upload_public(self.API_BASE_URL, self.headers, task_type, model_type, ticker, file_paths)
        else:
            if model_type != "llama" and model_type != "mistral":
                return {"error": "Model type is not valid. Please enter a valid model type"}
            return upload_private(task_type, model_type, ticker, file_paths)

    def train(self, model_name, fine_tuning_type, x_train_csv, y_train_csv, document_files, model_type = ModelType.FTGPT, is_private=False):
        """
        Train or Fine Tune a model via supervised or unsupervised fine tuning

        Args:
            model_name (str): The name of the model - which is referenced in the model_ids table alongside the model_id.
            model_type (str): Model that is used to do the fine tuning - could be "FT-GPT", "Llama3" for supervised, "MLM" for unsupervised.
            fine_tuning_type (str): The type of fine tuning - could be "supervised" or "unsupervised"
            x_train_csv (string of csv file path): training data for fine tuning - for each row could contain question or context entries
            y_train_csv (string of csv file path): training labels for fine tuning - for each row could contain answer entries
            document_files (list[str], optional): A list of file paths to documents for document-based tasks for training. Example: ['path/to/file1.pdf', 'path/to/file2.pdf'].
            is_private: The user can designate if they want to train a private model - will default to "Llama3" but can choose "Mistral"

        Returns:
            response (dict): A JSON response from the API, including the `model_id` of the trained model.
        """
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

    def predict(self, model_name, model_id, question_text, context_text=None, question_csv=None, document_files = None, model_type = ModelType.GPT):
        """Make predictions based on a dataset uploaded.

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

        if self.is_private == False:
            url = f"{self.API_BASE_URL}/public/chat"
            data = {
                "chat_id": chat_id,
                "message": message,
                "model_key": finetuned_model_key
            }
            response = requests.post(url, json=data, headers=self.headers)
            return response.json()
        else:
            return chat_private(chat_id, message, finetuned_model_key)


    def evaluate(self, message_id):
        """Evaluate predictions on one or multiple documents/text.

        Args:
            message_id (str): The ID of the message associated with the uploaded documents. This ID is used to identify which set of documents/text predictions should be evaluated.

        Returns:
            response (dict): A JSON response from the API, containing the evaluation results, `answer_relevancy`, `faithfulness` of the predictions on the specified message's documents or text. If the message ID is not provided or invalid, the function returns an error message indicating that a valid message ID is required for the operation.
        """

        if not message_id:
            return {"error": "Dataset ID is not set. Please create a dataset first."}

        if self.is_private == False:
            url = f"{self.API_BASE_URL}/public/evaluate"
            data = {'message_id': message_id}
            response = requests.post(url, json=data, headers=self.headers)
            return response.json()
        else:
            return evaluate_private(message_id)
        
# def process_meeting_notes(text, credentials_dict):
#     """
#     Extracts meeting details, checks weather, and schedules events.
#     """
#     meetings = handler_ai_agents.extract_meeting_details(text)

#     if not meetings:
#         return {"message": "No valid meetings found in the document."}

#     if not credentials_dict:
#         return {"error": "User not authenticated. Please log in."}

#     creds = Credentials.from_authorized_user_info(credentials_dict)

#     # ✅ Refresh token if expired
#     if creds.expired and creds.refresh_token:
#         try:
#             creds.refresh(Request())
#             session["google_credentials"] = credentials_to_dict(creds)  # ✅ Store refreshed credentials
#             session.modified = True
#             print("🔄 Credentials refreshed and saved!")
#         except Exception as e:
#             return {"error": f"Failed to refresh credentials: {str(e)}"}

#     calendar_agent = CalendarAgent(creds)
#     weather_agent = WeatherAgent()

#     scheduled_meetings = []
#     for meeting in meetings:
#         meeting_date = datetime.fromisoformat(meeting["start_time"]).strftime("%Y-%m-%d")
#         location = "New York"  # Hardcoded location

#         # ✅ Check weather before scheduling
#         weather_info = weather_agent.fetch_weather(meeting_date)

#         if "rain" in weather_info["condition"].lower() or "storm" in weather_info["condition"].lower():
#             print(f"⚠️ Bad weather detected for {meeting_date}: {weather_info['condition']}")
#             suggested_location = "Indoor Conference Room"
#             meeting["title"] += f" (Moved to {suggested_location})"

#         # ✅ Schedule meeting
#         result = calendar_agent.schedule_event(
#             meeting["title"],
#             meeting["start_time"],
#             1,  
#             "UTC"
#         )
#         scheduled_meetings.append({"meeting": meeting, "weather": weather_info, "calendar_result": result})

#     return {"message": f"{len(scheduled_meetings)} meetings scheduled.", "meetings": scheduled_meetings}

# def credentials_to_dict(credentials):
#     """Converts credentials object to a dictionary."""
#     return {
#         "token": credentials.token,
#         "refresh_token": credentials.refresh_token,
#         "token_uri": credentials.token_uri,
#         "client_id": credentials.client_id,
#         "client_secret": credentials.client_secret,
#         "scopes": credentials.scopes,
#     }
