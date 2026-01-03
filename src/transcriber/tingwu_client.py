"""阿里云听悟客户端封装"""

import time
from typing import Any, Dict, List

import requests
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tingwu20220930 import models as tingwu_models
from alibabacloud_tingwu20220930.client import Client as AlibabaTingwuClient

from src.utils.logger import get_logger
from src.utils.retry import APIError, NetworkError, with_retry


class TingwuClient:
    """阿里云听悟API客户端"""

    def __init__(self, config: Dict[str, str]):
        """
        初始化听悟客户端

        Args:
            config: 包含access_key_id, access_key_secret, region, app_key的配置字典
        """
        self.config = config
        self.app_key = config.get("app_key")
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.region = config.get("region", "cn-shanghai")
        self.logger = get_logger()

        # Validate configuration
        if not all([self.app_key, self.access_key_id, self.access_key_secret]):
            raise ValueError("Tingwu configuration incomplete")

        # Initialize Tingwu Client
        try:
            client_config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
            )
            client_config.region_id = self.region
            client_config.endpoint = "tingwu.cn-shanghai.aliyuncs.com"
            self.client = AlibabaTingwuClient(client_config)
            self.logger.info("Tingwu client initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize Tingwu client: {e}")
            raise NetworkError(f"Tingwu client initialization failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def submit_transcription_task(self, file_url: str, **kwargs) -> str:
        """
        提交音频转录任务

        Args:
            file_url: 音频文件URL
            **kwargs: 其他可选参数，如language_hints, vocabulary等

        Returns:
            任务ID
        """
        self.logger.info(f"Submitting transcription task for: {file_url}")

        # 构建请求参数
        task_payload = {
            "Input": {"FileUrl": file_url},
            "Parameters": {
                "Format": "mp3",
                "SampleRate": "16000",
                "Language": "zh-CN",
                "Model": "paraformer-v1",
                "OutputFormat": "txt",
            },
        }

        # Add optional parameters
        if "language_hints" in kwargs:
            task_payload["Parameters"]["LanguageHints"] = kwargs["language_hints"]

        # Add vocabulary if provided
        if "vocabulary" in kwargs:
            task_payload["Parameters"]["Vocabulary"] = kwargs["vocabulary"]

        try:
            # Create request
            request = tingwu_models.CreateFileTransRequest()
            request.body = task_payload

            # Submit task
            response = self.client.create_file_trans(request)
            response_data = response.body.to_map()

            # Extract task ID
            task_id = response_data.get("task_id")
            if not task_id:
                raise APIError(f"No task ID in response: {response_data}")

            self.logger.info(f"Transcription task submitted: {task_id}")
            return task_id

        except Exception as e:
            self.logger.error(f"Failed to submit transcription task: {e}")
            raise APIError(f"Tingwu task submission failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get transcription task status

        Args:
            task_id: Task ID to check

        Returns:
            Task status dictionary
        """
        self.logger.debug(f"Checking task status: {task_id}")

        try:
            # Create request
            request = tingwu_models.GetFileTransRequest()
            request.task_id = task_id

            # Get status
            response = self.client.get_file_trans(request)
            response_data = response.body.to_map()

            status = response_data.get("status", "UNKNOWN")
            self.logger.debug(f"Task {task_id} status: {status}")

            return response_data

        except Exception as e:
            self.logger.error(f"Failed to get task status: {e}")
            raise APIError(f"Tingwu status check failed: {e}")

    def wait_for_completion(self, task_id: str, timeout: int = 3600, poll_interval: int = 30) -> Dict[str, Any]:
        """
        Wait for transcription task to complete

        Args:
            task_id: Task ID to wait for
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            Final task result
        """
        self.logger.info(f"Waiting for task completion: {task_id}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status_data = self.get_task_status(task_id)
                status = status_data.get("status", "UNKNOWN")

                if status == "SUCCESS":
                    self.logger.info(f"Task {task_id} completed successfully")
                    return status_data
                elif status == "FAILED":
                    error_msg = status_data.get("error_code", "Unknown error")
                    self.logger.error(f"Task {task_id} failed: {error_msg}")
                    raise APIError(f"Transcription task failed: {error_msg}")

                self.logger.debug(f"Task {task_id} status: {status}, continuing to wait...")
                time.sleep(poll_interval)

            except APIError as e:
                if "failed" in str(e).lower():
                    raise
                self.logger.warning(f"Error checking task status, retrying: {e}")
                time.sleep(poll_interval)

        raise APIError(f"Task {task_id} timed out after {timeout} seconds")

    def get_transcription_result(self, task_id: str) -> str:
        """
        Get transcription result text

        Args:
            task_id: Completed task ID

        Returns:
            Transcription text
        """
        self.logger.info(f"Getting transcription result for: {task_id}")

        try:
            status_data = self.get_task_status(task_id)
            result_url = status_data.get("result_url")

            if not result_url:
                raise APIError("No result URL in task response")

            # Download result
            response = requests.get(result_url, timeout=30)
            response.raise_for_status()

            result_text = response.text
            self.logger.info(f"Retrieved transcription result: {len(result_text)} characters")
            return result_text

        except Exception as e:
            self.logger.error(f"Failed to get transcription result: {e}")
            raise APIError(f"Failed to retrieve transcription: {e}")

    def transcribe_audio(self, file_url: str, **kwargs) -> Dict[str, Any]:
        """
        Complete transcription workflow: submit task, wait for completion, get result

        Args:
            file_url: Audio file URL
            **kwargs: Additional parameters for transcription

        Returns:
            Structured transcription result dictionary
        """
        # Submit task
        task_id = self.submit_transcription_task(file_url, **kwargs)

        # Wait for completion
        status_data = self.wait_for_completion(task_id, **kwargs)

        # Get result text
        result_text = self.get_transcription_result(task_id)

        # Return structured format that matches transcript processor expectations
        return {
            "TaskId": task_id,
            "Status": "SUCCESS",
            "Result": {
                "Text": result_text,
                "Sentences": self._parse_sentences_from_text(result_text),
                "Duration": status_data.get("audio_duration", 0),
                "Language": "zh-CN",
                "WordCount": len(result_text.split()),
            },
        }

    def _parse_sentences_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse text into sentence-like segments for compatibility

        Args:
            text: Raw transcription text

        Returns:
            List of sentence dictionaries
        """
        # Simple sentence splitting by punctuation
        import re

        # Split by Chinese punctuation or periods
        sentences = re.split(r"[。！？；]", text)

        result_sentences = []
        current_time = 0

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Estimate timing (rough approximation)
            sentence_length = len(sentence)
            estimated_duration = sentence_length * 0.2  # Rough estimate: 0.2s per character

            result_sentences.append(
                {
                    "Text": sentence,
                    "BeginTime": current_time,
                    "EndTime": current_time + estimated_duration,
                    "SpeakerId": 0,  # Default speaker
                    "Confidence": 0.95,  # High confidence for Tingwu
                }
            )

            current_time += estimated_duration

        return result_sentences


if __name__ == "__main__":
    # Example usage
    config = {
        "app_key": "your_app_key",
        "access_key_id": "your_access_key_id",
        "access_key_secret": "your_access_key_secret",
        "region": "cn-shanghai",
    }

    client = TingwuClient(config)

    # Example transcription
    file_url = "https://your-audio-file-url.mp3"
    result = client.transcribe_audio(file_url)
    print(f"Transcription result: {result}")
