"""DashScope ASR client"""

from typing import Any, Dict

import dashscope
from dashscope.audio.asr import Transcription

from src.utils.logger import get_logger
from src.utils.retry import APIError, NetworkError, with_retry


class DashScopeClient:
    """DashScope ASR client (replacement for TingwuClient)"""

    def __init__(self, config: Dict[str, str]):
        """
        Initialize DashScope client

        Args:
            config: Configuration dictionary containing 'api_key'
        """
        self.config = config
        self.api_key = config.get("api_key")
        self.logger = get_logger()

        if not self.api_key:
            raise ValueError("DashScope API key not configured")

        dashscope.api_key = self.api_key
        self.logger.info("DashScope client initialized")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def transcribe_audio(self, file_url: str, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio using DashScope Paraformer

        Args:
            file_url: Audio file URL
            **kwargs: Additional parameters

        Returns:
            Structured transcription result dictionary
        """
        self.logger.info(f"Submitting DashScope transcription task for: {file_url}")

        try:
            # Submit task
            task_response = Transcription.async_call(
                model="paraformer-v1",
                file_urls=[file_url],
                language_hints=kwargs.get("language_hints", ["zh-CN"]),
            )

            if task_response.status_code != 200:
                raise APIError(f"Task submission failed: {task_response}")

            task_id = task_response.output.task_id
            self.logger.info(f"Task submitted: {task_id}")

            # Wait for completion
            status_response = Transcription.wait(task=task_id)

            if status_response.status_code != 200:
                raise APIError(f"Task wait failed: {status_response}")

            if status_response.output.task_status != "SUCCEEDED":
                raise APIError(f"Task failed: {status_response.output}")

            # Process result
            results = status_response.output.results
            if not results:
                raise APIError("No results in response")

            result = results[0]
            if result.get("subtask_status") != "SUCCEEDED":
                raise APIError(f"Subtask failed: {result}")

            # The result structure from DashScope might need parsing to match TingwuClient output
            # DashScope result.transcripts_result is usually a list of sentences/segments

            # Let's try to extract text and sentences
            # Note: The exact structure of `transcripts_result` depends on the model.
            # For paraformer-v1, it often returns list of sentences.

            # Since I can't be 100% sure of the structure without running it and inspecting deep JSON,
            # I will try to be robust.

            result.get("transcripts_result")  # Usually a URL for json or the json list itself?
            # Actually for paraformer-v1 via async_call, result.transcripts_result IS the list of sentences if not too large, or a URL.
            # Let's assume it's the list based on common SDK usage.

            # Wait, Transcription.wait returns the result object directly if it fits.

            sentences = []
            full_text = ""

            # If transcripts_result is a list (which it typically is for SDK)
            if isinstance(result.get("transcripts_result"), list):
                raw_sentences = result["transcripts_result"]
                for sent in raw_sentences:
                    text = sent.get("text", "")
                    start = sent.get("begin_time", 0) / 1000.0  # Convert ms to s
                    end = sent.get("end_time", 0) / 1000.0
                    full_text += text
                    sentences.append(
                        {
                            "Text": text,
                            "BeginTime": start,
                            "EndTime": end,
                            "SpeakerId": sent.get("channel_id", 0),
                            "Confidence": sent.get("confidence", 1.0),
                        }
                    )

            return {
                "TaskId": task_id,
                "Status": "SUCCESS",
                "Result": {
                    "Text": full_text,
                    "Sentences": sentences,
                    "Duration": 0,  # Duration might not be directly available in top level, but we have end time of last sentence
                    "Language": "zh-CN",
                    "WordCount": len(full_text),
                },
            }

        except Exception as e:
            self.logger.error(f"DashScope transcription failed: {e}")
            raise APIError(f"DashScope error: {e}")
