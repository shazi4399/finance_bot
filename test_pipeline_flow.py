#!/usr/bin/env python3
"""
手动测试整个内容处理流程
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


from src.downloader.audio_extractor import AudioExtractor
from src.downloader.downloader import VideoDownloader
from src.feishu_renderer.feishu_renderer import FeishuRenderer
from src.llm_processor.llm_processor import LLMProcessor
from src.transcriber.transcriber import AudioTranscriber
from src.utils.config import Config
from src.utils.logger import get_logger
from src.utils.storage import OSSStorage


def test_full_pipeline():
    """测试完整的内容处理流程"""
    logger = get_logger()
    logger.info("=== 开始完整流程测试 ===")

    # 测试视频URL - 选择一个有语音内容的视频
    test_video_url = "https://www.bilibili.com/video/BV1V6q1BVEMD/?spm_id_from=333.337.search-card.all.click&vd_source=478760d39696568d6d304b530c6a8808"  # 这是一个示例URL，你可以替换成其他视频

    try:
        # 1. 初始化所有组件
        logger.info("1. 初始化组件...")
        config = Config()
        downloader = VideoDownloader(config)
        extractor = AudioExtractor(config)
        transcriber = AudioTranscriber(config)
        llm_processor = LLMProcessor(config)
        feishu_renderer = FeishuRenderer(config)
        storage = OSSStorage(config)

        logger.info("✅ 所有组件初始化成功")

        # 2. 下载视频
        logger.info(f"2. 下载视频: {test_video_url}")
        video_info = downloader.download_video(test_video_url)
        if not video_info:
            logger.error("视频下载失败")
            return False

        logger.info(f"✅ 视频下载成功: {video_info.get('title', 'Unknown')}")

        # 3. 提取音频
        logger.info("3. 提取音频...")
        audio_file = extractor.extract_audio(video_info["file_path"])
        if not audio_file:
            logger.error("音频提取失败")
            return False

        logger.info(f"✅ 音频提取成功: {audio_file}")

        # 4. 上传到OSS（如果需要）
        logger.info("4. 上传音频到OSS...")
        audio_url = storage.upload_file(audio_file, "test_audio")
        if not audio_url:
            logger.warning("OSS上传失败，使用本地文件路径")
            audio_url = f"file://{audio_file}"
        else:
            logger.info(f"✅ 音频上传成功: {audio_url}")

        # 5. 语音转录（使用通义听悟）
        logger.info("5. 开始语音转录（通义听悟）...")
        transcript_result = transcriber.transcribe_audio_file(
            audio_url,
            language_hints=["zh-CN"],
            timeout=600,  # 10分钟超时
            poll_interval=30,  # 每30秒检查一次
        )

        if not transcript_result:
            logger.error("语音转录失败")
            return False

        logger.info("✅ 语音转录成功")
        logger.info(f"转录文本长度: {len(transcript_result.get('text', ''))} 字符")
        logger.info(f"段落数量: {len(transcript_result.get('segments', []))}")

        # 6. 内容分析（使用通义千问）
        logger.info("6. 开始内容分析（通义千问）...")

        # 准备转录文本给LLM
        formatted_transcript = transcriber.format_for_llm(transcript_result)

        # 生成内容分析
        analysis_result = llm_processor.analyze_content(formatted_transcript)
        if not analysis_result:
            logger.error("内容分析失败")
            return False

        logger.info("✅ 内容分析成功")
        logger.info(f"分析结果包含: {list(analysis_result.keys())}")

        # 7. 生成飞书文档
        logger.info("7. 生成飞书文档...")

        # 准备文档内容
        document_content = {
            "title": f"视频内容分析: {video_info.get('title', 'Unknown')}",
            "transcript": transcript_result,
            "analysis": analysis_result,
            "video_info": video_info,
        }

        # 创建飞书文档
        document_result = feishu_renderer.create_document(document_content)
        if not document_result:
            logger.error("飞书文档创建失败")
            return False

        logger.info("✅ 飞书文档创建成功")
        logger.info(f"文档URL: {document_result.get('url', 'No URL')}")

        # 8. 清理临时文件
        logger.info("8. 清理临时文件...")
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
            if os.path.exists(video_info["file_path"]):
                os.remove(video_info["file_path"])
            logger.info("✅ 临时文件清理完成")
        except Exception as e:
            logger.warning(f"清理临时文件时出错: {e}")

        logger.info("=== 完整流程测试成功！===")
        return True

    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        return False


def test_with_simple_video():
    """使用一个简单的测试视频"""
    logger = get_logger()
    logger.info("=== 使用简单测试视频 ===")

    # 使用一个短小的测试视频URL

    try:
        config = Config()
        transcriber = AudioTranscriber(config)

        # 直接使用在线音频文件测试转录
        test_audio_url = "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"

        logger.info(f"测试音频转录: {test_audio_url}")
        result = transcriber.transcribe_audio_file(test_audio_url)

        if result:
            logger.info("✅ 转录功能正常")
            logger.info(f"转录结果: {result}")
            return True
        else:
            logger.error("❌ 转录功能异常")
            return False

    except Exception as e:
        logger.error(f"简单测试失败: {e}")
        return False


if __name__ == "__main__":
    print("=== 内容智能流水线测试 ===")

    # 先进行简单测试
    simple_ok = test_with_simple_video()

    if simple_ok:
        print("\n✅ 简单测试通过，可以进行完整流程测试")

        # 询问是否进行完整测试
        response = input("是否要进行完整流程测试？(需要有效的B站视频URL) [y/N]: ")
        if response.lower() == "y":
            print("\n--- 开始完整流程测试 ---")
            success = test_full_pipeline()

            if success:
                print("\n🎉 完整流程测试成功！")
                print("你的内容智能流水线已经完全就绪！")
            else:
                print("\n❌ 完整流程测试失败，请检查日志")
                sys.exit(1)
        else:
            print("\n✅ 基础测试完成，流水线功能正常")
    else:
        print("\n❌ 基础测试失败，需要检查配置")
        sys.exit(1)
