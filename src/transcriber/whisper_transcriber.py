"""Whisper转录器封装"""

import os
import tempfile
from typing import Dict

import requests
import whisper

from src.utils.logger import get_logger
from src.utils.retry import APIError, NetworkError, with_retry


class WhisperTranscriber:
    """Whisper转录器"""

    def __init__(self, config: Dict[str, str]):
        """
        初始化Whisper转录器

        Args:
            config: 配置字典，包含model_name等参数
        """
        self.config = config
        self.model_name = config.get("model_name", "base")  # base, small, medium, large
        self.logger = get_logger()

        # 加载模型
        try:
            self.model = whisper.load_model(self.model_name)
            self.logger.info(f"Whisper model loaded: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise NetworkError(f"Whisper model loading failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def download_audio(self, file_url: str, local_path: str) -> str:
        """
        下载音频文件到本地

        Args:
            file_url: 音频文件URL
            local_path: 本地保存路径

        Returns:
            本地文件路径
        """
        self.logger.info(f"Downloading audio from: {file_url}")

        try:
            response = requests.get(file_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"Audio downloaded to: {local_path}")
            return local_path

        except Exception as e:
            self.logger.error(f"Failed to download audio: {e}")
            raise NetworkError(f"Audio download failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def transcribe_audio(self, file_url: str, **kwargs) -> str:
        """
        转录音频文件

        Args:
            file_url: 音频文件URL
            **kwargs: 其他可选参数，如language等

        Returns:
            转录文本
        """
        self.logger.info(f"Transcribing audio: {file_url}")

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # 下载音频文件
            self.download_audio(file_url, temp_path)

            # 转录参数
            transcribe_kwargs = {
                "language": kwargs.get("language", "zh"),
                "task": "transcribe",
            }

            # 执行转录
            result = self.model.transcribe(temp_path, **transcribe_kwargs)
            transcription = result["text"]

            self.logger.info(f"Transcription completed: {len(transcription)} characters")
            return transcription

        except Exception as e:
            self.logger.error(f"Failed to transcribe audio: {e}")
            raise APIError(f"Audio transcription failed: {e}")
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def transcribe_local_file(self, file_path: str, **kwargs) -> str:
        """
        转录本地音频文件

        Args:
            file_path: 本地音频文件路径
            **kwargs: 其他可选参数，如language等

        Returns:
            转录文本
        """
        self.logger.info(f"Transcribing local audio: {file_path}")

        try:
            # 转录参数
            transcribe_kwargs = {
                "language": kwargs.get("language", "zh"),
                "task": "transcribe",
            }

            # 执行转录
            result = self.model.transcribe(file_path, **transcribe_kwargs)
            transcription = result["text"]

            self.logger.info(f"Transcription completed: {len(transcription)} characters")
            return transcription

        except Exception as e:
            self.logger.error(f"Failed to transcribe audio: {e}")
            raise APIError(f"Audio transcription failed: {e}")


if __name__ == "__main__":
    # Example usage
    config = {"model_name": "base"}

    transcriber = WhisperTranscriber(config)

    # Example transcription
    file_url = "https://your-audio-file-url.mp3"
    result = transcriber.transcribe_audio(file_url)
    print(f"Transcription result: {result}")
