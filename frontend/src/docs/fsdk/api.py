import requests
import json
import os
import re
from typing import List, Dict, Any

from handlers.public_handlers import *
from handlers.private_handlers import *

class Anote:
    def __init__(self, api_key, is_private):
        self.API_BASE_URL = 'http://localhost:5000'
        #self.API_BASE_URL = 'https://api.Anote.ai'
        self.is_private = is_private
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

    def upload(self, task_type, model_type, ticker=None, file_paths=None):

        """Upload documents or specify a ticker for data retrieval and Q&A. This method supports various tasks, such as uploading documents or querying the government's EDGAR database.

        Args:
            task_type (str): Specifies the type of task to perform. This can be document-based interaction (e.g., 'documents') or financial data analysis ('edgar').
            model_type (str): Determines the AI model to use for processing the request. Different model types available are 'gpt' for GPT-4 and 'claude' for Claude.
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

    def create_agent(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an agent with the given configuration.

        Args:
            request_body (dict): JSON body containing agent details.

        Returns:
            dict: JSON response from the server, typically including agent_id and status.
        """
        endpoint = "/api/agents"
        return self._make_request(endpoint=endpoint, data=request_body, method="POST")

    def assign_task(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assign a new task to an existing agent.

        Args:
            request_body (dict): JSON body with at least:
                - "agent_id": The ID of the agent to assign the task.
                - "description": The task description.

        Returns:
            dict: JSON response from the server, typically including task_id, agent_id, and status.
        """
        endpoint = "/api/tasks"
        return self._make_request(endpoint=endpoint, data=request_body, method="POST")

    def get_task_status(self, task_id: int) -> Dict[str, Any]:
        """
        Retrieve the status of a given task.

        Args:
            task_id (int): The ID of the task.

        Returns:
            dict: JSON response containing current status, progress details, etc.
        """
        endpoint = f"/api/tasks/{task_id}"
        return self._make_request(endpoint=endpoint, method="GET")

    def list_agents(self) -> Dict[str, Any]:
        """
        List all agents currently registered in the system.

        Returns:
            dict or list: JSON response with a list of agents (each agent may have fields like agent_id, type, status).
        """
        endpoint = "/api/agents"
        return self._make_request(endpoint=endpoint, method="GET")

    def delete_agent(self, agent_id: int) -> Dict[str, Any]:
        """
        Delete an existing agent by ID.

        Args:
            agent_id (int): The ID of the agent to delete.

        Returns:
            dict: JSON response confirming the deletion status.
        """
        endpoint = f"/api/agents/{agent_id}"
        return self._make_request(endpoint=endpoint, method="DELETE")

    def _make_request(self,
                      endpoint: str,
                      data: Optional[dict] = None,
                      method: str = "POST") -> Dict[str, Any]:
        """
        Internal helper to handle HTTP requests to the Anote API.

        Args:
            endpoint (str): The endpoint path (e.g. "/api/agents").
            data (dict, optional): The request payload for POST/PUT methods.
            method (str): The HTTP method to use. Default is "POST".

        Returns:
            dict: Decoded JSON response from the server.

        Raises:
            requests.exceptions.RequestException: If the request fails or
                the status code is not in the 2xx range.
        """
        url = f"{self.API_BASE_URL}{endpoint}"

        if method.upper() == "POST":
            headers = {**self.headers, "Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers)
        elif method.upper() == "GET":
            response = requests.get(url, headers=self.headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=self.headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                # If response is not JSON, return raw text or raise error
                return {"error": "Invalid JSON in response", "content": response.text}
        else:
            raise requests.exceptions.RequestException(
                f"Request to {url} failed with status code {response.status_code}: {response.text}"
            )