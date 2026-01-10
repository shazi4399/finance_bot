#!/usr/bin/env python3
"""
Test script for Content Intelligence Pipeline

Usage:
    # Full test (download video + upload + transcribe + feishu)
    python test_pipeline.py --mode full --bvid BV1xx411c7mD

    # Quick test (use existing OSS URL)
    python test_pipeline.py --mode quick --oss-url "https://..."

    # Test only transcription
    python test_pipeline.py --mode transcribe-only --oss-url "https://..."
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import Config
from src.utils.logger import get_logger
from src.downloader.downloader import VideoDownloader
from src.utils.storage import OSSStorage
from src.transcriber.transcriber import AudioTranscriber
from src.llm_processor.llm_processor import LLMProcessor
from src.feishu_renderer.feishu_renderer import FeishuRenderer


def test_full_pipeline(config: Config, bvid: str):
    """
    Test full pipeline: download -> extract -> upload -> transcribe -> analyze -> feishu

    Args:
        config: Configuration object
        bvid: Bilibili video ID (e.g., BV1xx411c7mD)
    """
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Starting FULL PIPELINE TEST")
    logger.info("=" * 60)

    try:
        # Step 1: Download and extract audio
        logger.info(f"\n[Step 1/6] Downloading video {bvid}...")
        downloader = VideoDownloader(config)

        video_info = {
            "bvid": bvid,
            "title": f"Test video {bvid}",
            "upload_time": "2024-01-01"
        }

        result = downloader.download_and_extract(video_info)
        if not result:
            logger.error("Failed to download/extract audio")
            return False

        audio_file_path, video_title = result
        logger.info(f"✓ Audio extracted: {audio_file_path}")
        logger.info(f"✓ Video title: {video_title}")

        # Step 2: Upload to OSS
        logger.info(f"\n[Step 2/6] Uploading to OSS...")
        oss_config = {
            "access_key_id": config.get("aliyun.access_key_id"),
            "access_key_secret": config.get("aliyun.access_key_secret"),
            "oss_endpoint": config.get("aliyun.oss_endpoint"),
            "oss_bucket": config.get("aliyun.oss_bucket"),
            "oss_prefix": config.get("storage.oss_prefix", "daily_transcribe"),
        }
        storage = OSSStorage(oss_config)
        oss_url = storage.upload_file(audio_file_path)
        logger.info(f"✓ OSS URL: {oss_url}")

        # Save OSS URL for future tests
        with open("last_oss_url.txt", "w") as f:
            f.write(oss_url)
        logger.info("✓ OSS URL saved to last_oss_url.txt for future quick tests")

        # Update video info
        video_info_full = {
            **video_info,
            "video_title": video_title,
            "audio_file_path": audio_file_path,
        }

        # Continue with transcription
        return test_transcription_and_feishu(config, oss_url, video_info_full)

    except Exception as e:
        logger.error(f"Full pipeline test failed: {e}", exc_info=True)
        return False


def test_transcription_and_feishu(config: Config, oss_url: str, video_info: dict = None):
    """
    Test transcription + LLM analysis + Feishu rendering

    Args:
        config: Configuration object
        oss_url: OSS URL of audio file
        video_info: Optional video information
    """
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Starting TRANSCRIPTION + FEISHU TEST")
    logger.info("=" * 60)

    if not video_info:
        video_info = {
            "bvid": "TEST",
            "video_title": "测试视频",
            "upload_time": "2024-01-01",
            "url": "https://www.bilibili.com/video/TEST"
        }

    try:
        # Step 3: Transcribe audio
        logger.info(f"\n[Step 3/6] Transcribing audio from OSS...")
        logger.info(f"OSS URL: {oss_url[:100]}...")

        transcriber = AudioTranscriber(config)
        transcript_data = transcriber.transcribe_audio_file(oss_url)

        if not transcript_data:
            logger.error("Transcription failed")
            return False

        logger.info(f"✓ Transcription completed")
        logger.info(f"  - Word count: {transcript_data.get('metadata', {}).get('word_count', 0)}")
        logger.info(f"  - Duration: {transcript_data.get('metadata', {}).get('duration', 0)}s")
        logger.info(f"  - Segments: {len(transcript_data.get('segments', []))}")
        logger.info(f"  - Speakers: {len(transcript_data.get('speakers', {}))}")

        # Preview transcript
        transcript_text = transcript_data.get('text', '')[:200]
        logger.info(f"  - Preview: {transcript_text}...")

        # Save transcript for debugging
        with open("last_transcript.json", "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        logger.info("✓ Transcript saved to last_transcript.json")

        # Step 4: Analyze with LLM
        logger.info(f"\n[Step 4/6] Analyzing content with LLM...")
        llm_processor = LLMProcessor(config)
        content_data = llm_processor.process_transcript(transcript_data, video_info)

        if not content_data:
            logger.error("Content analysis failed")
            return False

        logger.info(f"✓ Content analysis completed")
        logger.info(f"  - Title: {content_data.get('title', '')}")
        logger.info(f"  - Summary: {content_data.get('summary', '')[:100]}...")
        logger.info(f"  - Positions: {len(content_data.get('positions', []))}")
        logger.info(f"  - Quotes: {len(content_data.get('quotes', []))}")
        logger.info(f"  - Blocks: {len(content_data.get('blocks', []))}")

        # Save content data for debugging
        with open("last_content.json", "w", encoding="utf-8") as f:
            # Remove segments to reduce file size
            content_copy = content_data.copy()
            if 'segments' in content_copy:
                content_copy['segments'] = f"<{len(content_copy['segments'])} segments>"
            json.dump(content_copy, f, ensure_ascii=False, indent=2)
        logger.info("✓ Content data saved to last_content.json")

        # Step 5: Render Feishu document
        logger.info(f"\n[Step 5/6] Rendering Feishu document...")
        feishu_renderer = FeishuRenderer(config)
        doc_url = feishu_renderer.render_content(content_data)

        if not doc_url:
            logger.error("Feishu document rendering failed")
            return False

        logger.info(f"✓ Feishu document created")
        logger.info(f"  - URL: {doc_url}")

        # Save doc URL
        with open("last_feishu_url.txt", "w") as f:
            f.write(doc_url)
        logger.info("✓ Feishu URL saved to last_feishu_url.txt")

        # Step 6: Summary
        logger.info(f"\n[Step 6/6] Test Summary")
        logger.info("=" * 60)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info(f"OSS URL: {oss_url[:80]}...")
        logger.info(f"Feishu Document: {doc_url}")
        logger.info(f"Video Title: {content_data.get('title', '')}")
        logger.info(f"Word Count: {transcript_data.get('metadata', {}).get('word_count', 0)}")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Transcription and Feishu test failed: {e}", exc_info=True)
        return False


def test_transcription_only(config: Config, oss_url: str):
    """
    Test only transcription (for debugging)

    Args:
        config: Configuration object
        oss_url: OSS URL of audio file
    """
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Starting TRANSCRIPTION ONLY TEST")
    logger.info("=" * 60)

    try:
        logger.info(f"\nTranscribing audio from OSS...")
        logger.info(f"OSS URL: {oss_url}")

        transcriber = AudioTranscriber(config)
        transcript_data = transcriber.transcribe_audio_file(oss_url)

        if not transcript_data:
            logger.error("Transcription failed")
            return False

        logger.info(f"\n✓ Transcription completed successfully!")
        logger.info(f"  - Word count: {transcript_data.get('metadata', {}).get('word_count', 0)}")
        logger.info(f"  - Duration: {transcript_data.get('metadata', {}).get('duration', 0)}s")
        logger.info(f"  - Segments: {len(transcript_data.get('segments', []))}")
        logger.info(f"  - Speakers: {len(transcript_data.get('speakers', {}))}")

        # Show first few segments
        segments = transcript_data.get('segments', [])
        if segments:
            logger.info(f"\nFirst 3 segments:")
            for i, seg in enumerate(segments[:3], 1):
                logger.info(f"  {i}. [{seg.get('start_time', 0):.1f}s] {seg.get('text', '')}")

        # Save transcript
        with open("last_transcript.json", "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        logger.info("\n✓ Full transcript saved to last_transcript.json")

        return True

    except Exception as e:
        logger.error(f"Transcription test failed: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Content Intelligence Pipeline")
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "transcribe-only"],
        default="quick",
        help="Test mode: full (download+transcribe+feishu), quick (transcribe+feishu), transcribe-only"
    )
    parser.add_argument(
        "--bvid",
        type=str,
        help="Bilibili video ID (for full mode)"
    )
    parser.add_argument(
        "--oss-url",
        type=str,
        help="OSS URL (for quick/transcribe-only mode)"
    )

    args = parser.parse_args()

    # Load configuration
    config = Config("config.yaml")
    logger = get_logger()

    # Validate configuration
    if not config.validate_required():
        logger.error("Configuration validation failed")
        sys.exit(1)

    success = False

    if args.mode == "full":
        if not args.bvid:
            logger.error("--bvid is required for full mode")
            parser.print_help()
            sys.exit(1)
        success = test_full_pipeline(config, args.bvid)

    elif args.mode == "quick":
        oss_url = args.oss_url

        # Try to load last OSS URL if not provided
        if not oss_url and Path("last_oss_url.txt").exists():
            with open("last_oss_url.txt", "r") as f:
                oss_url = f.read().strip()
            logger.info(f"Using last OSS URL from file")

        if not oss_url:
            logger.error("--oss-url is required for quick mode (or run full mode first)")
            parser.print_help()
            sys.exit(1)

        success = test_transcription_and_feishu(config, oss_url)

    elif args.mode == "transcribe-only":
        oss_url = args.oss_url

        # Try to load last OSS URL if not provided
        if not oss_url and Path("last_oss_url.txt").exists():
            with open("last_oss_url.txt", "r") as f:
                oss_url = f.read().strip()
            logger.info(f"Using last OSS URL from file")

        if not oss_url:
            logger.error("--oss-url is required for transcribe-only mode")
            parser.print_help()
            sys.exit(1)

        success = test_transcription_only(config, oss_url)

    if success:
        logger.info("\n✅ Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
