#!/usr/bin/env python3
"""
Test full flow: Download -> OSS -> Transcribe -> Analyze -> Render -> Notify
Using a specific Bilibili video.
"""

import logging
import os
import sys
import time

# Add src to python path
sys.path.append(os.getcwd())

from src.pipeline import ContentIntelligencePipeline
from src.utils.config import Config
from src.utils.logger import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)


def main():
    logger = get_logger()
    logger.info("Starting Full Flow Test")

    # Load config
    config = Config("config.yaml")

    # Initialize pipeline
    try:
        pipeline = ContentIntelligencePipeline(config)
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        return

    # Define the test video
    test_video_info = {
        "bvid": "BV1UNBKBoE5A",
        "title": "Test Video",  # Real title will be fetched if possible, or this is used in mock
        "url": "https://www.bilibili.com/video/BV1UNBKBoE5A",
        "upload_time": int(time.time()),
        "author": "Test Author",
    }

    # Mock the downloader.check_new_videos to return our test video
    # But we want the REAL download process to happen, so we only mock the discovery part.
    # The pipeline calls:
    # 1. new_videos = self.downloader.check_new_videos()
    # 2. for video in new_videos: self._process_video(video)
    #
    # _process_video calls:
    # 1. processed_videos = self.downloader.process_new_videos()
    #    -> This calls check_new_videos() internally again!

    # Wait, let's look at pipeline.py _process_video logic again.
    # It calls `self.downloader.process_new_videos()`.
    # And `process_new_videos` in downloader.py calls `check_new_videos()`.

    # So if we mock check_new_videos, we control what gets processed.

    def mock_check_new_videos():
        logger.info("Mock check_new_videos called, returning test video.")
        return [test_video_info]

    pipeline.downloader.check_new_videos = mock_check_new_videos
    # pipeline.downloader.monitor.get_new_videos = MagicMock(return_value=[test_video_info])

    # Also need to make sure `monitor.get_video_url` works for this BVID.
    # The real monitor uses Bilibili API. If that fails (e.g. rate limit), download fails.
    # But let's assume it works or just construct the URL manually if needed.
    # src/downloader/downloader.py: video_url = self.monitor.get_video_url(bvid)
    # src/downloader/bilibili_monitor.py: return f"https://www.bilibili.com/video/{bvid}"

    # Run the pipeline check
    logger.info("Running pipeline check...")
    results = pipeline.run_check()

    logger.info("Pipeline check finished.")
    import json

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
