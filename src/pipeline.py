"""Main Content Intelligence Pipeline orchestrator"""

import os
import time
from datetime import datetime
from typing import Any, Dict

from src.downloader.downloader import VideoDownloader
from src.feishu_renderer.feishu_renderer import FeishuRenderer
from src.llm_processor.llm_processor import LLMProcessor
from src.transcriber.transcriber import AudioTranscriber
from src.utils.config import Config
from src.utils.logger import get_logger
from src.utils.storage import OSSStorage


class ContentIntelligencePipeline:
    """Main pipeline orchestrator"""

    def __init__(self, config: Config):
        """
        Initialize pipeline

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Validate configuration
        if not config.validate_required():
            raise ValueError("Configuration validation failed")

        # Initialize components
        self._init_components()

        # Pipeline statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "last_run": None,
            "errors": [],
        }

        self.logger.info("Content Intelligence Pipeline initialized")

    def _init_components(self):
        """Initialize pipeline components"""
        try:
            # Initialize OSS storage
            oss_config = {
                "access_key_id": self.config.get("aliyun.access_key_id"),
                "access_key_secret": self.config.get("aliyun.access_key_secret"),
                "oss_endpoint": self.config.get("aliyun.oss_endpoint"),
                "oss_bucket": self.config.get("aliyun.oss_bucket"),
                "oss_prefix": self.config.get("storage.oss_prefix", "daily_transcribe"),
            }
            self.storage = OSSStorage(oss_config)

            # Setup lifecycle rule for automatic cleanup
            cleanup_days = self.config.get("storage.cleanup_after_days", 1)
            self.storage.setup_lifecycle_rule(cleanup_days)

            # Initialize video downloader
            self.downloader = VideoDownloader(self.config)

            # Initialize audio transcriber
            self.transcriber = AudioTranscriber(self.config)

            # Initialize LLM processor
            self.llm_processor = LLMProcessor(self.config)

            # Initialize Feishu renderer
            self.feishu_renderer = FeishuRenderer(self.config)

            self.logger.info("All pipeline components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline components: {e}")
            raise

    def run_check(self) -> Dict[str, Any]:
        """
        Run a single pipeline check

        Returns:
            Pipeline execution statistics
        """
        self.logger.info("Starting pipeline check")

        start_time = time.time()
        results = {
            "start_time": datetime.now().isoformat(),
            "processed_videos": [],
            "failed_videos": [],
            "errors": [],
        }

        try:
            # Step 1: Check for new videos
            new_videos = self.downloader.check_new_videos()

            if not new_videos:
                self.logger.info("No new videos found")
                results["message"] = "No new videos found"
                return results

            self.logger.info(f"Found {len(new_videos)} new videos")

            # Process each video
            for video_info in new_videos:
                try:
                    video_result = self._process_video(video_info)

                    if video_result["success"]:
                        results["processed_videos"].append(video_result)
                        self.stats["successful"] += 1
                    else:
                        results["failed_videos"].append(video_result)
                        self.stats["failed"] += 1

                    self.stats["total_processed"] += 1

                except Exception as e:
                    self.logger.error(f"Failed to process video {video_info.get('bvid', 'unknown')}: {e}")
                    error_result = {
                        "video_info": video_info,
                        "success": False,
                        "error": str(e),
                        "stage": "unknown",
                    }
                    results["failed_videos"].append(error_result)
                    results["errors"].append(str(e))
                    self.stats["failed"] += 1
                    self.stats["total_processed"] += 1

            # Update statistics
            self.stats["last_run"] = datetime.now().isoformat()

            # Calculate execution time
            execution_time = time.time() - start_time
            results["execution_time"] = execution_time
            results["total_processed"] = len(new_videos)
            results["successful_count"] = len(results["processed_videos"])
            results["failed_count"] = len(results["failed_videos"])

            self.logger.info(
                f"Pipeline check completed: {results['successful_count']}/{results['total_processed']} videos processed successfully"
            )

            return results

        except Exception as e:
            self.logger.error(f"Pipeline check failed: {e}")
            results["error"] = str(e)
            results["execution_time"] = time.time() - start_time
            return results

    def _process_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single video through the pipeline

        Args:
            video_info: Video information dictionary

        Returns:
            Processing result dictionary
        """
        bvid = video_info.get("bvid", "unknown")
        self.logger.info(f"Processing video: {bvid}")

        result = {
            "video_info": video_info,
            "success": False,
            "stages": {},
            "doc_url": None,
            "error": None,
        }

        try:
            # Stage 1: Download and extract audio
            self.logger.info(f"Stage 1: Downloading audio for {bvid}")
            download_result = self.downloader.download_and_extract(video_info)

            if not download_result:
                raise Exception(f"Failed to download/extract audio for {bvid}")

            audio_file_path, video_title = download_result

            # Update video info with extracted title
            our_video = video_info.copy()
            our_video["audio_file_path"] = audio_file_path
            our_video["video_title"] = video_title

            result["stages"]["download"] = {
                "success": True,
                "audio_file_path": audio_file_path,
            }

            # Stage 2: Upload to OSS
            self.logger.info(f"Stage 2: Uploading audio to OSS for {bvid}")
            oss_url = self.storage.upload_file(audio_file_path)

            result["stages"]["upload"] = {"success": True, "oss_url": oss_url}

            # Stage 3: Transcribe audio
            self.logger.info(f"Stage 3: Transcribing audio for {bvid}")
            transcript_data = self.transcriber.transcribe_audio_file(oss_url)

            if not transcript_data:
                raise Exception("Transcription failed")

            result["stages"]["transcription"] = {
                "success": True,
                "word_count": transcript_data.get("metadata", {}).get("word_count", 0),
            }

            # Stage 4: Analyze content with LLM
            self.logger.info(f"Stage 4: Analyzing content for {bvid}")
            content_data = self.llm_processor.process_transcript(transcript_data, our_video)

            if not content_data:
                raise Exception("Content analysis failed")

            result["stages"]["analysis"] = {
                "success": True,
                "title": content_data.get("title", ""),
            }

            # Stage 5: Render Feishu document
            self.logger.info(f"Stage 5: Rendering Feishu document for {bvid}")
            doc_url = self.feishu_renderer.render_content(content_data)

            if not doc_url:
                raise Exception("Document rendering failed")

            result["stages"]["rendering"] = {"success": True, "doc_url": doc_url}

            # Mark as processed in history
            self.downloader.monitor.mark_video_processed(
                bvid=bvid,
                title=video_title,
                upload_time=video_info.get("upload_time", ""),
            )

            # Cleanup temporary files
            self.downloader.cleanup_temp_files([our_video])

            result["success"] = True
            result["doc_url"] = doc_url

            self.logger.info(f"Video {bvid} processed successfully: {doc_url}")

        except Exception as e:
            self.logger.error(f"Failed to process video {bvid}: {e}")
            result["error"] = str(e)

            # Determine which stage failed
            for stage_name, stage_data in result["stages"].items():
                if not stage_data.get("success", False):
                    result["stage"] = stage_name
                    break
            else:
                result["stage"] = "unknown"

        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics

        Returns:
            Statistics dictionary
        """
        return {
            **self.stats,
            "downloader_stats": self.downloader.get_stats(),
            "storage_info": self.storage.get_bucket_info(),
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components

        Returns:
            Health check results
        """
        self.logger.info("Performing pipeline health check")

        health_results = {
            "overall": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Check OSS connection
            try:
                bucket_info = self.storage.get_bucket_info()
                health_results["components"]["storage"] = {
                    "status": "healthy",
                    "info": bucket_info,
                }
            except Exception as e:
                health_results["components"]["storage"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_results["overall"] = "unhealthy"

            # Check downloader
            try:
                downloader_stats = self.downloader.get_stats()
                health_results["components"]["downloader"] = {
                    "status": "healthy",
                    "stats": downloader_stats,
                }
            except Exception as e:
                health_results["components"]["downloader"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_results["overall"] = "unhealthy"

            # Check configuration
            try:
                config_valid = self.config.validate_required()
                health_results["components"]["config"] = {
                    "status": "healthy" if config_valid else "unhealthy",
                    "valid": config_valid,
                }
                if not config_valid:
                    health_results["overall"] = "unhealthy"
            except Exception as e:
                health_results["components"]["config"] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_results["overall"] = "unhealthy"

            self.logger.info(f"Health check completed: {health_results['overall']}")

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            health_results["overall"] = "unhealthy"
            health_results["error"] = str(e)

        return health_results

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up pipeline resources")

        try:
            # Cleanup any temporary files
            temp_dir = self.config.get("storage.temp_dir", "/tmp/finance_bot")
            if os.path.exists(temp_dir):
                # Clean up old audio files
                current_time = time.time()
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > 3600:  # 1 hour
                            os.remove(file_path)
                            self.logger.debug(f"Cleaned up old file: {file_path}")

            self.logger.info("Pipeline cleanup completed")

        except Exception as e:
            self.logger.error(f"Pipeline cleanup failed: {e}")
