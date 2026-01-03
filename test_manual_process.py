#!/usr/bin/env python3
"""Manual processing of a specific video to verify the pipeline"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline import ContentIntelligencePipeline
from src.utils.config import Config
from src.utils.logger import setup_logger


def main():
    # Setup logging
    logger = setup_logger(name="pipeline", log_file="logs/test_manual.log", level="INFO")

    logger.info("Starting manual process test")

    try:
        # Load configuration
        config = Config("config.yaml")

        # Initialize pipeline
        pipeline = ContentIntelligencePipeline(config)

        # Manually define video info for the video we just downloaded
        video_info = {
            "bvid": "BV15CBYB2Ejk",
            "title": "第1092日投资记录：港股继续不开盘，今天更新一下exel表",
            "upload_time": "20251226",
            "url": "https://www.bilibili.com/video/BV15CBYB2Ejk",
        }

        # We already have the file at /tmp/finance_bot/BV15CBYB2Ejk.mp3
        # But pipeline._process_video will try to download it again.
        # Since our fix, it calls self.downloader.download_and_extract(video_info)
        # Which will see the file exists if it's smart, or just re-download it.

        logger.info(f"Processing video {video_info['bvid']}...")
        result = pipeline._process_video(video_info)

        if result["success"]:
            logger.info(f"Successfully processed video! Doc URL: {result['doc_url']}")
        else:
            logger.error(f"Failed to process video: {result.get('error')}")
            if "stage" in result:
                logger.error(f"Failed at stage: {result['stage']}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
