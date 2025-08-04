import requests
import os

class AnoteLeaderboardSubmission:
    def __init__(self, api_key):
        self.API_BASE_URL = 'http://localhost:5000'
        # self.API_BASE_URL = 'https://api.Anote.ai'
        self.headers = {
            'Authorization': f'Bearer {api_key}'
        }

    def add_model_to_dataset(self, benchmark_dataset_name, model_name, model_results):
        """
        Submit a model's results to a benchmark dataset

        Args:
            benchmark_dataset_name (str): Name of the benchmark dataset
            model_name (str): Name of the model
            model_results (list[str]): List of model outputs

        Returns:
            (bool, float): Success flag and score extracted from model_results
        """
        url = f"{self.API_BASE_URL}/public/submit_model"
        data = {
            "benchmarkDatasetName": benchmark_dataset_name,
            "modelName": model_name,
            "modelResults": model_results
        }

        try:
            response = requests.post(url, json=data, headers=self.headers)
            if response.status_code == 200:
                result = response.json()
                score = result.get("score", 0.0)
                return True, score
            else:
                print(f"[add_model_to_dataset] Failed with status code: {response.status_code}")
                return False, 0.0
        except Exception as e:
            print(f"[add_model_to_dataset] Exception: {e}")
            return False, 0.0

    def add_dataset_to_leaderboard(self, dataset_name, dataset_file_path, task_type):
        """
        Register a new dataset for leaderboard use

        Args:
            dataset_name (str): Name of the dataset
            dataset_file_path (str): Local file path to the dataset
            task_type (str): Type of task (qa, classification, ner)

        Returns:
            (bool, str): Success flag and dataset ID
        """
        url = f"{self.API_BASE_URL}/public/add_dataset"

        if not os.path.exists(dataset_file_path):
            print(f"[add_dataset_to_leaderboard] File not found: {dataset_file_path}")
            return False, ""

        try:
            with open(dataset_file_path, 'rb') as file:
                files = {
                    'file': (os.path.basename(dataset_file_path), file)
                }
                data = {
                    'datasetName': dataset_name,
                    'taskType': task_type
                }

                response = requests.post(url, data=data, files=files, headers=self.headers)

            if response.status_code == 200:
                result = response.json()
                dataset_id = result.get("datasetId", "")
                return True, dataset_id
            else:
                print(f"[add_dataset_to_leaderboard] Failed with status code: {response.status_code}")
                return False, ""
        except Exception as e:
            print(f"[add_dataset_to_leaderboard] Exception: {e}")
            return False, ""