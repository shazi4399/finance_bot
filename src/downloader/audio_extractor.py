"""Audio extraction from Bilibili videos"""

import os
from typing import Optional, Tuple

import ffmpeg
import yt_dlp

from src.utils.logger import get_logger
from src.utils.retry import NetworkError, with_retry


class AudioExtractor:
    """Extract audio from Bilibili videos"""

    def __init__(self, temp_dir: str = "/tmp/finance_bot", cookies_file: Optional[str] = None):
        """
        Initialize audio extractor

        Args:
            temp_dir: Temporary directory for downloaded files
            cookies_file: Path to Netscape formatted cookies file
        """
        self.temp_dir = temp_dir
        self.cookies_file = cookies_file
        self.logger = get_logger()

        # Ensure temp directory exists
        os.makedirs(temp_dir, exist_ok=True)

    @with_retry(max_attempts=3, exceptions=(NetworkError, Exception))
    def extract_audio(self, video_url: str, quality: str = "bestaudio") -> Tuple[str, str]:
        """
        Extract audio from video and convert to MP3

        Args:
            video_url: Video URL to extract audio from
            quality: Audio quality setting

        Returns:
            Tuple of (audio_file_path, video_title)
        """
        self.logger.info(f"Extracting audio from: {video_url}")

        # Setup yt-dlp options
        ydl_opts = {
            "format": quality,
            "outtmpl": os.path.join(self.temp_dir, "%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",  # 192 kbps
                }
            ],
            "quiet": True,
            "no_warnings": True,
            "extractaudio": True,
            "audioformat": "mp3",
        }

        # Use cookies file if provided, otherwise try browser cookies
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts["cookiefile"] = self.cookies_file
            self.logger.info(f"Using cookies file: {self.cookies_file}")
        else:
            # Fallback to browser cookies (might fail in server env)
            # ydl_opts['cookies_from_browser'] = 'chrome'
            # Commenting out browser cookies as it's unsafe in headless/server envs usually.
            pass

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(video_url, download=True)

                video_id = info.get("id", "")
                video_title = info.get("title", "Unknown Title")

                # Construct expected audio file path
                audio_file_path = os.path.join(self.temp_dir, f"{video_id}.mp3")

                # Verify file exists
                if not os.path.exists(audio_file_path):
                    # Try alternative naming
                    for file in os.listdir(self.temp_dir):
                        if file.startswith(video_id) and file.endswith(".mp3"):
                            audio_file_path = os.path.join(self.temp_dir, file)
                            break
                    else:
                        raise FileNotFoundError(f"Audio file not found for video {video_id}")

                # Get file size for logging
                file_size = os.path.getsize(audio_file_path) / (1024 * 1024)  # MB
                self.logger.info(f"Audio extracted: {audio_file_path} ({file_size:.2f} MB)")

                return audio_file_path, video_title

        except Exception as e:
            self.logger.error(f"Failed to extract audio: {e}")
            raise NetworkError(f"Audio extraction failed: {e}")

    def cleanup_temp_file(self, file_path: str):
        """
        Clean up temporary file

        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup file {file_path}: {e}")

    def get_audio_info(self, audio_file_path: str) -> dict:
        """
        Get audio file information

        Args:
            audio_file_path: Path to audio file

        Returns:
            Dictionary with audio information
        """
        try:
            probe = ffmpeg.probe(audio_file_path)
            audio_stream = next(
                (stream for stream in probe["streams"] if stream["codec_type"] == "audio"),
                None,
            )

            if audio_stream:
                return {
                    "duration": float(audio_stream.get("duration", 0)),
                    "bit_rate": int(audio_stream.get("bit_rate", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 0)),
                    "channels": int(audio_stream.get("channels", 0)),
                    "codec": audio_stream.get("codec_name", "unknown"),
                    "size": os.path.getsize(audio_file_path),
                }
            else:
                return {"error": "No audio stream found"}

        except Exception as e:
            self.logger.error(f"Failed to get audio info: {e}")
            return {"error": str(e)}

    def validate_audio_file(self, audio_file_path: str) -> bool:
        """
        Validate audio file is usable for transcription

        Args:
            audio_file_path: Path to audio file

        Returns:
            True if file is valid, False otherwise
        """
        if not os.path.exists(audio_file_path):
            self.logger.error(f"Audio file does not exist: {audio_file_path}")
            return False

        # Get file info
        info = self.get_audio_info(audio_file_path)

        # Check for errors
        if "error" in info:
            self.logger.error(f"Audio file error: {info['error']}")
            return False

        # Check duration (should be at least 1 second)
        if info.get("duration", 0) < 1:
            self.logger.error(f"Audio duration too short: {info.get('duration', 0)} seconds")
            return False

        # Check file size (should be reasonable)
        size_mb = info.get("size", 0) / (1024 * 1024)
        if size_mb > 500:  # 500MB limit for most transcription services
            self.logger.error(f"Audio file too large: {size_mb:.2f} MB")
            return False

        self.logger.info(f"Audio file validated: {size_mb:.2f} MB, {info.get('duration', 0):.2f} seconds")
        return True
