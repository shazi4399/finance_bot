#!/usr/bin/env python3
"""
辅助脚本：从B站下载视频，提取音频，上传到OSS

用法:
    uv run python download_and_upload.py --bvid BV1xx411c7mD
"""

import argparse
import sys

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.downloader.audio_extractor import AudioExtractor
from src.utils.storage import OSSStorage


def download_and_upload(bvid: str):
    """
    从B站下载视频，提取音频，上传到OSS

    Args:
        bvid: B站视频BV号
    """
    logger = setup_logger("download", level="INFO")
    logger.info("=" * 80)
    logger.info("B站视频下载 → 音频提取 → OSS上传")
    logger.info("=" * 80)

    try:
        # 加载配置
        config = Config("config.yaml")
        logger.info("✓ 配置加载成功")

        # 步骤 1: 提取音频
        logger.info(f"\n[步骤 1/2] 从B站下载视频并提取音频")
        logger.info(f"BVID: {bvid}")
        logger.info("-" * 80)

        temp_dir = config.get("storage.temp_dir", "/tmp/finance_bot")
        cookies_file = config.get("monitoring.cookies_file")

        extractor = AudioExtractor(temp_dir=temp_dir, cookies_file=cookies_file)

        video_url = f"https://www.bilibili.com/video/{bvid}"
        logger.info(f"视频链接: {video_url}")
        logger.info("开始下载和提取音频...")

        audio_file_path, video_title = extractor.extract_audio(video_url)

        logger.info(f"\n✅ 音频提取成功！")
        logger.info(f"  • 视频标题: {video_title}")
        logger.info(f"  • 音频文件: {audio_file_path}")

        # 验证音频文件
        if not extractor.validate_audio_file(audio_file_path):
            logger.error("❌ 音频文件验证失败")
            return None

        # 步骤 2: 上传到OSS
        logger.info(f"\n[步骤 2/2] 上传音频到OSS")
        logger.info("-" * 80)

        oss_config = {
            "access_key_id": config.get("aliyun.access_key_id"),
            "access_key_secret": config.get("aliyun.access_key_secret"),
            "oss_endpoint": config.get("aliyun.oss_endpoint"),
            "oss_bucket": config.get("aliyun.oss_bucket"),
            "oss_prefix": config.get("storage.oss_prefix", "daily_transcribe"),
        }

        storage = OSSStorage(oss_config)
        logger.info("开始上传到OSS...")

        oss_url = storage.upload_file(audio_file_path)

        logger.info(f"\n✅ 上传成功！")
        logger.info(f"OSS URL: {oss_url}")

        # 保存URL到文件
        with open("last_oss_url.txt", "w") as f:
            f.write(oss_url)

        logger.info("\n" + "=" * 80)
        logger.info("✅ 完成！OSS URL 已保存到 last_oss_url.txt")
        logger.info("=" * 80)
        logger.info("\n下一步：运行测试脚本")
        logger.info("  uv run python test_improved_features.py")
        logger.info("\n或者指定URL:")
        logger.info(f'  uv run python test_improved_features.py --oss-url "{oss_url}"')

        # 清理本地文件
        logger.info("\n清理本地音频文件...")
        extractor.cleanup_temp_file(audio_file_path)

        return oss_url

    except Exception as e:
        logger.error(f"❌ 失败: {e}", exc_info=True)
        return None


def main():
    parser = argparse.ArgumentParser(description="从B站下载视频并上传到OSS")
    parser.add_argument(
        "--bvid",
        type=str,
        required=True,
        help="B站视频BV号 (例如: BV1xx411c7mD)"
    )

    args = parser.parse_args()

    oss_url = download_and_upload(args.bvid)

    if oss_url:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
