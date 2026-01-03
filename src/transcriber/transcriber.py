"""Main transcriber module combining Tingwu ASR and result processing"""

from typing import Any, Dict, Optional

from src.utils.config import Config
from src.utils.logger import get_logger

from .tingwu_client import TingwuClient
from .transcript_processor import TranscriptProcessor


class AudioTranscriber:
    """Main audio transcriber class"""

    def __init__(self, config: Config):
        """
        Initialize audio transcriber

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize Tingwu client (using Aliyun credentials)
        tingwu_config = {
            "app_key": config.get("tingwu.app_key"),
            "access_key_id": config.get("aliyun.access_key_id"),
            "access_key_secret": config.get("aliyun.access_key_secret"),
            "region": config.get("aliyun.region", "cn-shanghai"),
        }

        self.client = TingwuClient(tingwu_config)
        self.processor = TranscriptProcessor()

        # Default transcription parameters
        self.default_params = {
            "diarization_enabled": True,
            "auto_chapters": True,
            "speaker_labels": True,
            "language_hints": ["zh-CN", "en-US"],
            "timeout": 3600,
            "poll_interval": 30,
        }

    def transcribe_audio_file(self, file_url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio file and return processed result

        Args:
            file_url: URL of audio file to transcribe
            **kwargs: Additional transcription parameters

        Returns:
            Processed transcription result or None if failed
        """
        self.logger.info(f"Transcribing audio file: {file_url}")

        # Merge with default parameters
        params = {**self.default_params, **kwargs}

        try:
            # Transcribe using Tingwu
            raw_result = self.client.transcribe_audio(file_url, **params)

            if not raw_result:
                self.logger.error(f"Transcription failed for: {file_url}")
                return None

            # Process result
            processed_result = self.processor.process_transcript(raw_result)

            # Add file URL to result
            processed_result["source_url"] = file_url

            self.logger.info(f"Transcription completed for: {file_url}")
            return processed_result

        except Exception as e:
            self.logger.error(f"Transcription failed for {file_url}: {e}")
            return None

    def transcribe_multiple_files(self, file_urls: list, **kwargs) -> list:
        """
        Transcribe multiple audio files

        Args:
            file_urls: List of audio file URLs
            **kwargs: Additional transcription parameters

        Returns:
            List of processed transcription results
        """
        self.logger.info(f"Transcribing {len(file_urls)} audio files")

        results = []

        for i, file_url in enumerate(file_urls, 1):
            self.logger.info(f"Processing file {i}/{len(file_urls)}: {file_url}")

            result = self.transcribe_audio_file(file_url, **kwargs)
            if result:
                results.append(result)
            else:
                self.logger.warning(f"Failed to transcribe file: {file_url}")

        self.logger.info(f"Completed transcription for {len(results)}/{len(file_urls)} files")
        return results

    def format_for_llm(self, transcript: Dict[str, Any]) -> str:
        """
        Format transcript for LLM consumption

        Args:
            transcript: Processed transcript dictionary

        Returns:
            Formatted text string
        """
        return self.processor.format_for_llm(transcript)

    def get_transcript_summary(self, transcript: Dict[str, Any]) -> str:
        """
        Get transcript summary

        Args:
            transcript: Processed transcript dictionary

        Returns:
            Summary text
        """
        return transcript.get("summary", "")

    def get_transcript_text(self, transcript: Dict[str, Any]) -> str:
        """
        Get full transcript text

        Args:
            transcript: Processed transcript dictionary

        Returns:
            Full text
        """
        return transcript.get("text", "")

    def get_transcript_segments(self, transcript: Dict[str, Any]) -> list:
        """
        Get transcript segments

        Args:
            transcript: Processed transcript dictionary

        Returns:
            List of segments
        """
        return transcript.get("segments", [])

    def get_speaker_info(self, transcript: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get speaker information

        Args:
            transcript: Processed transcript dictionary

        Returns:
            Speaker information dictionary
        """
        return transcript.get("speakers", {})

    def get_chapters(self, transcript: Dict[str, Any]) -> list:
        """
        Get chapter information

        Args:
            transcript: Processed transcript dictionary

        Returns:
            List of chapters
        """
        return transcript.get("chapters", [])

    def get_metadata(self, transcript: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get transcript metadata

        Args:
            transcript: Processed transcript dictionary

        Returns:
            Metadata dictionary
        """
        return transcript.get("metadata", {})
