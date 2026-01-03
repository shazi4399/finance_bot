"""Main downloader module combining monitoring and audio extraction"""

from typing import Dict, List, Optional, Tuple

from src.utils.config import Config
from src.utils.logger import get_logger

from .audio_extractor import AudioExtractor
from .bilibili_monitor import BilibiliMonitor


class VideoDownloader:
    """Main downloader class that combines monitoring and audio extraction"""

    def __init__(self, config: Config):
        """
        Initialize video downloader

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize components
        uid = config.get("monitoring.bilibili_uid")
        if not uid:
            raise ValueError("Bilibili UID not configured")

        cookies_file = config.get("monitoring.cookies_file")
        self.monitor = BilibiliMonitor(uid=uid, history_db="data/video_history.db", cookies_file=cookies_file)

        temp_dir = config.get("storage.temp_dir", "/tmp/finance_bot")
        self.extractor = AudioExtractor(temp_dir=temp_dir, cookies_file=cookies_file)

        self.max_videos = config.get("monitoring.max_videos_per_check", 5)

    def check_new_videos(self) -> List[Dict[str, str]]:
        """
        Check for new videos

        Returns:
            List of new video information
        """
        self.logger.info("Checking for new videos...")

        try:
            new_videos = self.monitor.get_new_videos(limit=self.max_videos)

            for video in new_videos:
                self.logger.info(f"New video found: {video['bvid']} - {video['title']}")

            return new_videos

        except Exception as e:
            self.logger.error(f"Failed to check for new videos: {e}")
            return []

    def download_and_extract(self, video_info: Dict[str, str]) -> Optional[Tuple[str, str]]:
        """
        Download video and extract audio

        Args:
            video_info: Video information dictionary

        Returns:
            Tuple of (audio_file_path, video_title) or None if failed
        """
        bvid = video_info.get("bvid")
        if not bvid:
            self.logger.error("Video BVID not found in video info")
            return None

        try:
            # Get full video URL
            video_url = self.monitor.get_video_url(bvid)

            # Extract audio
            audio_file_path, video_title = self.extractor.extract_audio(video_url)

            # Validate audio file
            if not self.extractor.validate_audio_file(audio_file_path):
                self.logger.error(f"Audio validation failed for {bvid}")
                self.extractor.cleanup_temp_file(audio_file_path)
                return None

            self.logger.info(f"Successfully extracted audio for {bvid}: {audio_file_path}")
            return audio_file_path, video_title

        except Exception as e:
            self.logger.error(f"Failed to download/extract audio for {bvid}: {e}")
            return None

    def process_new_videos(self) -> List[Dict[str, str]]:
        """
        Process all new videos and return extracted audio information

        Returns:
            List of dictionaries with video info and audio file paths
        """
        # Get new videos
        new_videos = self.check_new_videos()

        if not new_videos:
            self.logger.info("No new videos found")
            return []

        processed_videos = []

        for video_info in new_videos:
            bvid = video_info.get("bvid")

            try:
                # Download and extract audio
                result = self.download_and_extract(video_info)

                if result:
                    audio_file_path, video_title = result

                    # Add audio path to video info
                    video_info_with_audio = video_info.copy()
                    video_info_with_audio["audio_file_path"] = audio_file_path
                    video_info_with_audio["video_title"] = video_title

                    processed_videos.append(video_info_with_audio)

                    # Mark as processed
                    self.monitor.mark_video_processed(
                        bvid=bvid,
                        title=video_title,
                        upload_time=video_info.get("upload_time", ""),
                    )
                else:
                    self.logger.warning(f"Failed to process video {bvid}")

            except Exception as e:
                self.logger.error(f"Error processing video {bvid}: {e}")

        self.logger.info(f"Processed {len(processed_videos)} new videos")
        return processed_videos

    def cleanup_temp_files(self, video_list: List[Dict[str, str]]):
        """
        Clean up temporary audio files

        Args:
            video_list: List of video dictionaries with audio_file_path
        """
        for video in video_list:
            audio_path = video.get("audio_file_path")
            if audio_path:
                self.extractor.cleanup_temp_file(audio_path)

    def get_stats(self) -> Dict[str, int]:
        """
        Get downloader statistics

        Returns:
            Dictionary with statistics
        """
        return {"processed_count": self.monitor.get_processed_count()}
