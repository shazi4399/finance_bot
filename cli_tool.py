#!/usr/bin/env python3
"""
CLI Tool for testing individual components of the Content Intelligence Pipeline.
This tool allows you to run each stage of the pipeline independently.

Usage:
    python cli_tool.py download --bvid <BVID>
    python cli_tool.py upload --file <AUDIO_FILE>
    python cli_tool.py transcribe --url <OSS_URL>
    python cli_tool.py summarize --transcript <TRANSCRIPT_JSON> --video-info <VIDEO_INFO_JSON>
    python cli_tool.py feishu --content <CONTENT_JSON>
"""

import argparse
import json
import os
import sys
from typing import Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.downloader.downloader import VideoDownloader
from src.feishu_renderer.feishu_renderer import FeishuRenderer
from src.llm_processor.llm_processor import LLMProcessor
from src.transcriber.transcriber import AudioTranscriber
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.utils.storage import OSSStorage

# Setup logging
logger = setup_logger(name="cli_tool", level="INFO")


def load_config(config_path: str = "config.yaml") -> Config:
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    return Config(config_path)


def save_json(data: Any, filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved output to {filename}")


def load_json(filename: str) -> Any:
    if not os.path.exists(filename):
        logger.error(f"File not found: {filename}")
        sys.exit(1)
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_download(args):
    config = load_config(args.config)
    downloader = VideoDownloader(config)

    logger.info(f"Downloading video: {args.bvid}")

    # Construct video info
    video_info = {
        "bvid": args.bvid,
        "title": f"Manual Download {args.bvid}",
        "upload_time": "unknown",
    }

    result = downloader.download_and_extract(video_info)

    if result:
        audio_file_path, video_title = result
        logger.info(f"Success! Audio file: {audio_file_path}")
        logger.info(f"Video Title: {video_title}")

        # Update video info with real title
        video_info["title"] = video_title
        video_info["video_title"] = video_title
        video_info["audio_file_path"] = audio_file_path

        save_json(video_info, f"{args.bvid}_info.json")
    else:
        logger.error("Download failed")
        sys.exit(1)


def cmd_upload(args):
    config = load_config(args.config)

    oss_config = {
        "access_key_id": config.get("aliyun.access_key_id"),
        "access_key_secret": config.get("aliyun.access_key_secret"),
        "oss_endpoint": config.get("aliyun.oss_endpoint"),
        "oss_bucket": config.get("aliyun.oss_bucket"),
        "oss_prefix": config.get("storage.oss_prefix", "daily_transcribe"),
    }

    storage = OSSStorage(oss_config)

    logger.info(f"Uploading file: {args.file}")
    url = storage.upload_file(args.file)

    logger.info(f"Upload success! OSS URL: {url}")
    print(url)  # Print to stdout for easy piping


def cmd_transcribe(args):
    config = load_config(args.config)
    transcriber = AudioTranscriber(config)

    logger.info(f"Transcribing URL: {args.url}")
    result = transcriber.transcribe_audio_file(args.url)

    if result:
        logger.info("Transcription success!")
        output_file = "transcript.json"
        save_json(result, output_file)
    else:
        logger.error("Transcription failed")
        sys.exit(1)


def cmd_summarize(args):
    config = load_config(args.config)
    llm = LLMProcessor(config)

    transcript_data = load_json(args.transcript)
    video_info = load_json(args.video_info) if args.video_info else {"title": "Unknown Video", "bvid": "unknown"}

    logger.info("Summarizing transcript...")
    result = llm.process_transcript(transcript_data, video_info)

    if result:
        logger.info("Summarization success!")
        output_file = "summary.json"
        save_json(result, output_file)
    else:
        logger.error("Summarization failed")
        sys.exit(1)


def cmd_feishu(args):
    config = load_config(args.config)
    feishu = FeishuRenderer(config)

    content_data = load_json(args.content)

    logger.info("Rendering to Feishu...")
    doc_url = feishu.render_content(content_data)

    if doc_url:
        logger.info(f"Feishu document created: {doc_url}")
    else:
        logger.error("Feishu rendering failed")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Content Intelligence Pipeline CLI Tool")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Download command
    parser_download = subparsers.add_parser("download", help="Download video and extract audio")
    parser_download.add_argument("--bvid", required=True, help="Bilibili Video ID")
    parser_download.set_defaults(func=cmd_download)

    # Upload command
    parser_upload = subparsers.add_parser("upload", help="Upload audio file to OSS")
    parser_upload.add_argument("--file", required=True, help="Path to audio file")
    parser_upload.set_defaults(func=cmd_upload)

    # Transcribe command
    parser_transcribe = subparsers.add_parser("transcribe", help="Transcribe audio from OSS URL")
    parser_transcribe.add_argument("--url", required=True, help="OSS URL of the audio file")
    parser_transcribe.set_defaults(func=cmd_transcribe)

    # Summarize command
    parser_summarize = subparsers.add_parser("summarize", help="Summarize transcript using LLM")
    parser_summarize.add_argument("--transcript", required=True, help="Path to transcript JSON file")
    parser_summarize.add_argument("--video-info", help="Path to video info JSON file (optional)")
    parser_summarize.set_defaults(func=cmd_summarize)

    # Feishu command
    parser_feishu = subparsers.add_parser("feishu", help="Send summary to Feishu")
    parser_feishu.add_argument("--content", required=True, help="Path to summary content JSON file")
    parser_feishu.set_defaults(func=cmd_feishu)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
