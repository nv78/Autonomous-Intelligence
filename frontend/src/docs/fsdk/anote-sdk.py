import json
import requests
# from constants import *
from enum import IntEnum
from typing import List, Optional, Dict, Any

class Agent:
    """
    Represents an AI-driven entity, configured with a model and optional default Task.
    """

    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        task: Optional["Task"] = None,
        tools: Optional[List[str]] = None,
        verbose: bool = False
    ):
        """
        Args:
            name (str): Short identifier for the agent (e.g., 'FinanceAgent').
            model (str): Underlying LLM (e.g., 'gpt4', 'gpt3.5turbo', 'llama').
            system_prompt (str): A top-level prompt or role instruction (e.g., 'You are an event planner.').
            task (Task, optional): A default Task object this Agent is responsible for.
            tools (list of str, optional): Names of tools the Agent can call (e.g., 'ScrapeWebsiteTool').
            verbose (bool): If True, logs extra debug info.
        """
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.task = task
        self.tools = tools or []
        self.verbose = verbose

    def __repr__(self):
        return f"<Agent name={self.name} model={self.model} verbose={self.verbose}>"


class Task:
    """
    Represents a discrete assignment or objective for an Agent.
    """

    def __init__(
        self,
        instructions: str,
        files_uploaded: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
        expected_output: str = "",
        agent: Optional[Agent] = None
    ):
        """
        Args:
            instructions (str): The main prompt or directive for the Agent.
            files_uploaded (list of str, optional): File paths or IDs relevant to the Task (e.g., PDFs, CSVs).
            examples (list, optional): Few-shot examples or reference data.
            expected_output (str): Form or content of the final result (e.g., 'Return a markdown summary').
            agent (Agent, optional): The Agent assigned to this Task.
        """
        self.instructions = instructions
        self.files_uploaded = files_uploaded or []
        self.examples = examples or []
        self.expected_output = expected_output
        self.agent = agent

    def __repr__(self):
        return f"<Task instructions={self.instructions[:25]}... expected_output={self.expected_output[:25]}...>"


class Crew:
    """
    Represents a collaborative group of Agents and the Tasks they must complete.
    """

    def __init__(
        self,
        agents: Optional[List[Agent]] = None,
        tasks: Optional[List[Task]] = None,
        verbose: bool = False
    ):
        """
        Args:
            agents (list of Agent, optional): Agents that will collaborate on Tasks.
            tasks (list of Task, optional): Tasks to be completed by these Agents.
            verbose (bool): If True, logs more details during execution.
        """
        self.agents = agents or []
        self.tasks = tasks or []
        self.verbose = verbose

    def __repr__(self):
        return f"<Crew agents={len(self.agents)} tasks={len(self.tasks)} verbose={self.verbose}>"

    def kickoff(self, inputs: Dict[str, Any] = None):
        """
        Starts or orchestrates the tasks in some manner.
        Customize as needed for your logic (sequential, parallel, hierarchical, etc.).
        """
        if self.verbose:
            print(f"[Crew] Kicking off with inputs: {inputs}")
        # Example: Just prints out each task's instructions
        for task in self.tasks:
            if self.verbose:
                print(f"[Crew] Running task: {task.instructions}")
        return {"status": "completed", "inputs_used": inputs}


class Tools:
    """
    Represents an external capability or integration (e.g., web search, data fetch).
    """

    def __init__(
        self,
        tool_name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            tool_name (str): Identifier for the tool (e.g., 'ScrapeWebsiteTool').
            config (dict, optional): Configuration details (e.g., API keys, parameters).
        """
        self.tool_name = tool_name
        self.config = config or {}

    def __repr__(self):
        return f"<Tool tool_name={self.tool_name}>"


class Workflow:
    """
    Defines the method by which tasks are executed within a Crew.
    """

    def __init__(
        self,
        workflow_type: str = "sequential",
        manager_agent: Optional[Agent] = None,
        allow_parallel: bool = False
    ):
        """
        Args:
            workflow_type (str): e.g., 'sequential', 'hierarchical', or 'parallel'.
            manager_agent (Agent, optional): Used in hierarchical workflows.
            allow_parallel (bool): If True, tasks may run concurrently.
        """
        self.workflow_type = workflow_type
        self.manager_agent = manager_agent
        self.allow_parallel = allow_parallel

    def __repr__(self):
        return (f"<Workflow type={self.workflow_type} "
                f"manager_agent={self.manager_agent} "
                f"allow_parallel={self.allow_parallel}>")

class NLPTask(IntEnum):
    TEXT_CLASSIFICATION = 0
    NAMED_ENTITY_RECOGNITION = 1
    PROMPTING = 2
    CHATBOT = 3
    UNSUPERVISED = 4

class ModelType(IntEnum):
    NO_LABEL_TEXT_CLASSIFICATION = 0
    FEW_SHOT_TEXT_CLASSIFICATION = 1
    NAIVE_BAYES_TEXT_CLASSIFICATION = 2
    SETFIT_TEXT_CLASSIFICATION = 3
    NOT_ALL_TEXT_CLASSIFICATION = 4
    FEW_SHOT_NAMED_ENTITY_RECOGNITION = 5
    EXAMPLE_BASED_NAMED_ENTITY_RECOGNITION = 6
    GPT_FOR_PROMPTING = 7
    PROMPT_NAMED_ENTITY_RECOGNITION = 8
    PROMPTING_WITH_FEEDBACK_PROMPT_ENGINEERED = 9
    DUMMY = 10
    GPT_FINETUNING = 11
    RAG_UNSUPERVISED = 12
    ZEROSHOT_GPT4 = 13
    ZEROSHOT_CLAUDE = 14
    ZEROSHOT_LLAMA3 = 15
    ZEROSHOT_MISTRAL = 16
    ZEROSHOT_GPT4MINI = 17
    ZEROSHOT_GEMINI = 18

class ZeroShotModelType(IntEnum):
    ZERO_SHOT_GPT4 = 0
    ZERO_SHOT_CLAUDE = 1
    ZERO_SHOT_LLAMA3 = 2
    ZERO_SHOT_MISTRAL = 3
    ZERO_SHOT_GPT4_MINI = 4
    ZERO_SHOT_GEMINI = 5


class EvaluationMetric(IntEnum):
    COSINE_SIM = 0
    BERT_SCORE = 1
    ROUGE_L_F1 = 2
    FAITHFULNESS = 3
    ANSWER_RELEVANCE = 4
    ANOTE_MISLABEL_SCORE = 5
    CONFUSION_MATRIX = 6
    CLASSIFICATION_REPORT = 7
    PRECISION = 8
    RECALL = 9
    F1 = 10
    IOU = 11
    SUPPORT = 12

class Anote:
    def __init__(self, api_key):
        self.API_BASE_URL = 'http://localhost:5000'
        # self.API_BASE_URL = 'https://api.anote.ai'
        self.headers = {
            # 'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

    def train(self, task_type: NLPTask, model_type: ModelType, dataset_name, multi_column_roots, input_text_col_index, document_files=None):
        """
        Train a model with the given parameters.

        Args:
            task_type (str): The type of task (e.g., classification, regression).
            model_type (str): The type of model to train.
            dataset_name (str): The name of the dataset.
            multi_column_roots (list): A list of column roots.
            input_text_col_index (int): The index of the input text column.
            document_files (list): List of paths to document files, if any.

        Returns:
            str: The model ID if training is successful.
        """
        task_type_int = None
        if task_type is not None:
            task_type_int = task_type.value
        model_type_int = None
        if model_type is not None:
            model_type_int = model_type.value
        data = {
            "taskType": task_type_int,
            "modelType": model_type_int,
            "datasetName": dataset_name,
            "multiColumnRoots": multi_column_roots,
            "inputTextColIndex": input_text_col_index,
        }
        files, opened_files = _open_files(document_files)
        response = self._make_request('/public/train', data, files=files)
        return response

    def predictAll(self, report_name, model_types, model_id, dataset_id, actual_label_col_index, input_text_col_index, document_files=None):
        """
        Predict on an entire dataset using the specified model.

        Args:
            model_id (str): The ID of the model to use for prediction.
            datasetId (str): The ID of the dataset to predict on.
            input_text_col_index (int): The index of the input text column.
            document_files (list): List of paths to document files, if any.

        Returns:
            dict: A dictionary containing the predictions.
        """
        data = {
            "modelId": model_id,
            "modelTypes": model_types,
            "reportName": report_name,
            "datasetId": dataset_id,
            "actualLabelColIndex": actual_label_col_index,
            "inputTextColIndex": input_text_col_index,
        }
        files, opened_files = _open_files(document_files)
        response = self._make_request('/public/predictAll', data, files=files)
        return response

    def predict(self, model_id, text, model_type = None, document_files=None):
        """
        Predict on a single piece of text using the specified model.

        Args:
            model_id (str): The ID of the model to use for prediction.
            text (str): The text to predict on.
            document_files (list): List of paths to document files, if any.

        Returns:
            str: The prediction result.
        """
        model_type_int = None
        if model_type is not None:
            model_type_int = model_type.value
        data = {
            "modelId": model_id,
            "text": text,
            "modelType": model_type_int
        }
        files, opened_files = _open_files(document_files)
        response = self._make_request('/public/predict', data, files=files)
        return response

    def evaluate(self, metrics: List[EvaluationMetric], task_type, report_name, dataset_id=None, multi_column_roots=None, input_text_col_index=None, document_files=None):
        """
        Evaluate the model performance using the given metrics.

        Args:
            metrics (dict): The evaluation metrics.
            dataset_id (str, optional): The ID of the dataset.
            multi_column_roots (list, optional): A list of column roots.
            input_text_col_index (int, optional): The index of the input text column.
            document_files (list, optional): List of paths to document files, if any.

        Returns:
            dict: A dictionary containing evaluation results.
        """
        task_type_int = None
        if task_type is not None:
            task_type_int = task_type.value

        data = {
            "metrics": json.dumps(metrics),
            "datasetId": dataset_id,
            "multiColumnRoots": multi_column_roots,
            "inputTextColIndex": input_text_col_index,
            "taskType": task_type_int,
            "reportName": report_name,
        }
        files, opened_files = _open_files(document_files)
        response = self._make_request('/public/evaluate', data, files=files)
        return response

    def checkStatus(self, predict_report_id=None, model_id=None):
        """
        Check the status of a prediction or training process.

        Args:
            predict_report_id (str, optional): The ID of the prediction report.
            model_id (str, optional): The ID of the model.

        Returns:
            bool: True if the process is complete, False otherwise.
        """
        data = {
            "predictReportId": predict_report_id,
            "modelId": model_id,
        }
        response = self._make_request('/public/checkStatus', data)
        return response

    def viewPredictions(self, predict_report_id, dataset_id, search_query, page_number):
        """
        View predictions for a given dataset and query.

        Args:
            predict_report_id (str): The ID of the prediction report.
            dataset_id (str): The ID of the dataset.
            search_query (str): The search query to filter predictions.
            page_number (int): The page number of the results.

        Returns:
            dict: A dictionary containing the predictions.
        """
        data = {
            "predictReportId": predict_report_id,
            "datasetId": dataset_id,
            "searchQuery": search_query,
            "pageNumber": page_number,
        }
        response = self._make_request('/public/viewPredictions', data)
        return response

    def __init__(self, api_key: str, base_url: str = "http://localhost:5000"):
        """
        Initialize the Anote SDK client.

        Args:
            api_key (str): The API key for authentication.
            base_url (str): The base URL of the Anote API.
        """
        self.API_BASE_URL = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}"
        }


    def _make_request(self, endpoint, data, files=None):
        url = f"{self.API_BASE_URL}{endpoint}"

        if files:
            # For multipart/form-data
            response = requests.post(url, data=data, headers=self.headers, files=files)
        else:
            # For application/json
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            response = requests.post(url, json=data, headers=headers)

        # _close_files(files)  # Uncomment if you need to close files

        if response.status_code == 200:
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                raise ValueError(f"Failed to decode JSON response for {endpoint}")
        else:
            raise requests.exceptions.RequestException(f"Request to {endpoint} failed with status code {response.status_code}")


def _open_files(document_files):
    if document_files is None:
        return {}, []

    files = []
    opened_files = []
    for path in document_files:
        try:
            file = open(path, 'rb')
            opened_files.append(file)
            files.append(("files[]", (path.split('/')[-1], file, "application/octet-stream")))
        except Exception as e:
            print(f"Error opening file {path}: {e}")
            _close_files(opened_files)
            raise e
    return files, opened_files

def _close_files(opened_files):
    for file in opened_files:
        file.close()
