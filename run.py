#!/usr/bin/env python3
"""
一键运行脚本 - 自动化处理B站视频

使用方法:
    uv run python run.py --bvid BV1xx411c7mD
"""

import argparse
import sys
import time
from pathlib import Path

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.downloader.audio_extractor import AudioExtractor
from src.utils.storage import OSSStorage
from src.transcriber.transcriber import AudioTranscriber
from src.llm_processor.llm_processor import LLMProcessor
from src.feishu_renderer.feishu_renderer import FeishuRenderer


def run_pipeline(bvid: str, skip_download: bool = False, oss_url: str = None):
    """
    一键运行完整流程

    Args:
        bvid: B站视频BV号
        skip_download: 是否跳过下载（使用已有的OSS URL）
        oss_url: 已有的OSS URL（如果skip_download=True）
    """
    logger = setup_logger("run", level="INFO")

    logger.info("=" * 80)
    logger.info("🚀 Finance Bot - 一键运行")
    logger.info("=" * 80)

    try:
        # 加载配置
        config = Config("config.yaml")
        logger.info("✓ 配置加载成功\n")

        video_info = {
            "bvid": bvid,
            "video_title": f"视频 {bvid}",
            "upload_time": time.strftime("%Y-%m-%d")
        }

        # ========== 步骤 1: 下载和上传 ==========
        if not skip_download:
            logger.info("=" * 80)
            logger.info("📥 步骤 1/4: 下载视频并提取音频")
            logger.info("=" * 80)

            temp_dir = config.get("storage.temp_dir", "/tmp/finance_bot")
            cookies_file = config.get("monitoring.cookies_file")
            extractor = AudioExtractor(temp_dir=temp_dir, cookies_file=cookies_file)

            video_url = f"https://www.bilibili.com/video/{bvid}"
            logger.info(f"视频链接: {video_url}")
            logger.info("开始下载和提取音频...")

            audio_file_path, video_title = extractor.extract_audio(video_url)
            video_info["video_title"] = video_title

            logger.info(f"✅ 音频提取成功")
            logger.info(f"  • 视频标题: {video_title}")
            logger.info(f"  • 音频文件: {audio_file_path}\n")

            # 上传到OSS
            logger.info("📤 上传音频到OSS...")
            oss_config = {
                "access_key_id": config.get("aliyun.access_key_id"),
                "access_key_secret": config.get("aliyun.access_key_secret"),
                "oss_endpoint": config.get("aliyun.oss_endpoint"),
                "oss_bucket": config.get("aliyun.oss_bucket"),
                "oss_prefix": config.get("storage.oss_prefix", "daily_transcribe"),
            }
            storage = OSSStorage(oss_config)
            oss_url = storage.upload_file(audio_file_path)

            logger.info(f"✅ OSS上传成功")
            logger.info(f"  • OSS URL: {oss_url[:100]}...\n")

            # 保存URL
            with open("last_oss_url.txt", "w") as f:
                f.write(oss_url)

            # 清理本地文件
            extractor.cleanup_temp_file(audio_file_path)
        else:
            logger.info("⏭️  跳过下载，使用已有OSS URL\n")

        # ========== 步骤 2: 语音转文字 ==========
        logger.info("=" * 80)
        logger.info("🎙️  步骤 2/4: 语音转文字")
        logger.info("=" * 80)
        logger.info(f"OSS URL: {oss_url[:100]}...")
        logger.info("开始转录，这可能需要几分钟...\n")

        transcriber = AudioTranscriber(config)
        transcript_data = transcriber.transcribe_audio_file(oss_url)

        if not transcript_data:
            logger.error("❌ 转录失败")
            return False

        logger.info(f"✅ 转录成功")
        logger.info(f"  • 总字数: {transcript_data.get('metadata', {}).get('word_count', 0)}")
        logger.info(f"  • 时长: {transcript_data.get('metadata', {}).get('duration', 0)} 秒")
        logger.info(f"  • 分段数: {len(transcript_data.get('segments', []))}")
        logger.info(f"  • 说话人数: {len(transcript_data.get('speakers', {}))}\n")

        # ========== 步骤 3: LLM分析 ==========
        logger.info("=" * 80)
        logger.info("🤖 步骤 3/4: LLM内容分析")
        logger.info("=" * 80)
        logger.info("分析内容中...\n")

        llm_processor = LLMProcessor(config)
        content_data = llm_processor.process_transcript(transcript_data, video_info)

        if not content_data:
            logger.error("❌ 内容分析失败")
            return False

        logger.info(f"✅ 内容分析成功")
        logger.info(f"  • 标题: {content_data.get('title', '')}")
        logger.info(f"  • 持仓变动: {len(content_data.get('positions', []))} 条")
        logger.info(f"  • 核心金句: {len(content_data.get('quotes', []))} 条\n")

        # ========== 步骤 4: 飞书渲染 ==========
        logger.info("=" * 80)
        logger.info("📄 步骤 4/4: 飞书文档生成")
        logger.info("=" * 80)
        logger.info("创建飞书文档...\n")

        feishu_renderer = FeishuRenderer(config)
        doc_url = feishu_renderer.render_content(content_data)

        if not doc_url:
            logger.error("❌ 飞书文档创建失败")
            return False

        logger.info(f"✅ 飞书文档创建成功")
        logger.info(f"  • 文档链接: {doc_url}\n")

        # 保存文档链接
        with open("last_feishu_url.txt", "w") as f:
            f.write(doc_url)

        # ========== 完成 ==========
        logger.info("=" * 80)
        logger.info("🎉 处理完成！")
        logger.info("=" * 80)
        logger.info(f"视频: {video_info['video_title']}")
        logger.info(f"BVID: {bvid}")
        logger.info(f"文档: {doc_url}")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 处理失败: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="一键运行 Finance Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整流程（下载 + 转录 + 分析 + 飞书）
  uv run python run.py --bvid BV1xx411c7mD

  # 跳过下载，使用已有OSS URL
  uv run python run.py --bvid BV1xx411c7mD --skip-download --oss-url "https://..."

  # 使用保存的OSS URL
  uv run python run.py --bvid BV1xx411c7mD --skip-download
        """
    )
    parser.add_argument(
        "--bvid",
        type=str,
        required=True,
        help="B站视频BV号 (例如: BV1xx411c7mD)"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="跳过下载，使用已有的OSS URL"
    )
    parser.add_argument(
        "--oss-url",
        type=str,
        help="OSS音频URL（配合--skip-download使用）"
    )

    args = parser.parse_args()

    # 检查参数
    if args.skip_download:
        oss_url = args.oss_url

        # 尝试从文件读取
        if not oss_url and Path("last_oss_url.txt").exists():
            with open("last_oss_url.txt", "r") as f:
                oss_url = f.read().strip()
            print(f"使用保存的OSS URL: {oss_url[:80]}...")

        if not oss_url:
            print("错误: --skip-download 需要提供 --oss-url 或存在 last_oss_url.txt")
            sys.exit(1)
    else:
        oss_url = None

    # 运行流程
    success = run_pipeline(args.bvid, skip_download=args.skip_download, oss_url=oss_url)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
