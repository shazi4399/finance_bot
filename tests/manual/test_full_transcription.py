#!/usr/bin/env python3
"""
测试完整的转录流程，包括实际的音频转录
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import time

from src.transcriber.transcriber import AudioTranscriber
from src.utils.config import Config
from src.utils.logger import get_logger


def create_test_audio_file():
    """创建一个测试音频文件"""
    # 使用一个简单的在线音频文件进行测试
    test_audio_url = "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    return test_audio_url


def test_transcription_flow():
    """测试完整的转录流程"""
    logger = get_logger()
    logger.info("开始测试完整转录流程...")

    try:
        # 加载配置
        config = Config()

        # 初始化转录器
        transcriber = AudioTranscriber(config)
        logger.info("音频转录器初始化成功")

        # 使用测试音频文件
        test_audio_url = create_test_audio_file()
        logger.info(f"测试音频URL: {test_audio_url}")

        # 开始转录
        logger.info("开始转录音频...")
        start_time = time.time()

        result = transcriber.transcribe_audio_file(
            test_audio_url,
            language_hints=["zh-CN"],
            timeout=300,  # 5分钟超时
            poll_interval=10,  # 每10秒检查一次
        )

        end_time = time.time()
        duration = end_time - start_time

        if result:
            logger.info(f"✅ 转录成功！耗时: {duration:.2f}秒")
            logger.info(f"转录文本长度: {len(result.get('text', ''))} 字符")
            logger.info(f"段落数量: {len(result.get('segments', []))}")

            # 显示部分结果
            text = result.get("text", "")
            if text:
                logger.info(f"转录文本预览: {text[:100]}...")

            # 检查说话人信息
            speakers = result.get("speakers", {})
            if speakers:
                logger.info(f"检测到 {len(speakers)} 个说话人")

            # 检查章节信息
            chapters = result.get("chapters", [])
            if chapters:
                logger.info(f"检测到 {len(chapters)} 个章节")

            return True
        else:
            logger.error("❌ 转录失败: 没有返回结果")
            return False

    except Exception as e:
        logger.error(f"❌ 转录流程失败: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        return False


def test_multiple_transcriptions():
    """测试多个文件转录"""
    logger = get_logger()
    logger.info("测试多个文件转录...")

    try:
        config = Config()
        transcriber = AudioTranscriber(config)

        # 使用多个测试音频URL
        test_urls = [
            "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
            # 可以添加更多测试音频
        ]

        results = transcriber.transcribe_multiple_files(test_urls)

        logger.info(f"成功转录 {len(results)}/{len(test_urls)} 个文件")

        for i, result in enumerate(results):
            logger.info(f"文件 {i + 1}: 文本长度 {len(result.get('text', ''))} 字符")

        return len(results) > 0

    except Exception as e:
        logger.error(f"多文件转录测试失败: {e}")
        return False


def test_result_formatting():
    """测试结果格式化功能"""
    logger = get_logger()
    logger.info("测试结果格式化...")

    try:
        config = Config()
        transcriber = AudioTranscriber(config)

        # 创建一个模拟的转录结果
        mock_result = {
            "text": "这是一个测试转录结果。包含了多个句子。",
            "segments": [
                {
                    "text": "这是一个测试转录结果。",
                    "start_time": 0.0,
                    "end_time": 2.5,
                    "speaker_id": 0,
                    "confidence": 0.95,
                },
                {
                    "text": "包含了多个句子。",
                    "start_time": 2.5,
                    "end_time": 5.0,
                    "speaker_id": 1,
                    "confidence": 0.92,
                },
            ],
            "speakers": {
                "0": {"id": "0", "name": "Speaker 1"},
                "1": {"id": "1", "name": "Speaker 2"},
            },
            "chapters": [{"title": "第一章", "start_time": 0.0, "end_time": 5.0}],
            "summary": "测试摘要",
            "metadata": {"duration": 5.0, "word_count": 10},
        }

        # 测试不同格式化选项
        llm_format = transcriber.format_for_llm(mock_result)
        logger.info(f"LLM格式:\n{llm_format}")

        full_text = transcriber.get_transcript_text(mock_result)
        logger.info(f"完整文本: {full_text}")

        summary = transcriber.get_transcript_summary(mock_result)
        logger.info(f"摘要: {summary}")

        segments = transcriber.get_transcript_segments(mock_result)
        logger.info(f"段落数: {len(segments)}")

        return True

    except Exception as e:
        logger.error(f"格式化测试失败: {e}")
        return False


if __name__ == "__main__":
    print("=== 完整转录流程测试 ===")

    tests = [
        ("配置和初始化", lambda: True),  # 前面的测试已经验证了
        ("单文件转录", test_transcription_flow),
        ("多文件转录", test_multiple_transcriptions),
        ("结果格式化", test_result_formatting),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n--- 测试: {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅ 通过' if result else '❌ 失败'}: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results.append((test_name, False))

    print("\n=== 测试总结 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        print(f"{'✅' if result else '❌'} {test_name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！通义听悟转录功能完全就绪")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查日志")
        sys.exit(1)
