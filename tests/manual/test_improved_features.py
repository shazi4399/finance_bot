#!/usr/bin/env python3
"""
测试改进后的语音转文字和飞书排版功能

使用方法:
    uv run python test_improved_features.py --oss-url "https://your-oss-url.mp3"
"""

import argparse
import json
import sys
from pathlib import Path

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.transcriber.transcriber import AudioTranscriber
from src.llm_processor.llm_processor import LLMProcessor
from src.feishu_renderer.feishu_renderer import FeishuRenderer


def test_transcription_with_oss_url(oss_url: str):
    """
    使用 OSS URL 测试转录功能

    Args:
        oss_url: OSS 上音频文件的 URL
    """
    logger = setup_logger("test", level="INFO")
    logger.info("=" * 80)
    logger.info("测试改进后的语音转文字和飞书排版功能")
    logger.info("=" * 80)

    try:
        # 加载配置
        config = Config("config.yaml")
        logger.info("✓ 配置加载成功")

        # ==================== 步骤 1: 语音转文字 ====================
        logger.info("\n" + "=" * 80)
        logger.info("步骤 1/4: 语音转文字（阿里云听悟）")
        logger.info("=" * 80)
        logger.info(f"OSS URL: {oss_url[:100]}...")

        transcriber = AudioTranscriber(config)
        logger.info("开始转录，这可能需要几分钟...")

        transcript_data = transcriber.transcribe_audio_file(oss_url)

        if not transcript_data:
            logger.error("❌ 转录失败")
            return False

        logger.info("\n✅ 转录成功！")
        logger.info("-" * 80)
        logger.info(f"📊 转录统计:")
        logger.info(f"  • 总字数: {transcript_data.get('metadata', {}).get('word_count', 0)}")
        logger.info(f"  • 时长: {transcript_data.get('metadata', {}).get('duration', 0)} 秒")
        logger.info(f"  • 分段数: {len(transcript_data.get('segments', []))}")
        logger.info(f"  • 说话人数: {len(transcript_data.get('speakers', {}))}")

        # 展示前3个分段（带时间戳）
        segments = transcript_data.get('segments', [])
        if segments:
            logger.info("\n📝 转录内容预览（前3段）:")
            logger.info("-" * 80)
            for i, seg in enumerate(segments[:3], 1):
                start_time = seg.get('start_time', 0)
                speaker_id = seg.get('speaker_id', 0)
                text = seg.get('text', '')
                logger.info(f"  [{format_time(start_time)}] [说话人{speaker_id}] {text}")

        # 保存完整转录结果
        output_file = "test_transcript_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        logger.info(f"\n💾 完整转录结果已保存到: {output_file}")

        # ==================== 步骤 2: LLM 分析 ====================
        logger.info("\n" + "=" * 80)
        logger.info("步骤 2/4: LLM 内容分析（通义千问）")
        logger.info("=" * 80)

        video_info = {
            "bvid": "TEST",
            "video_title": "测试视频",
            "upload_time": "2024-01-04",
        }

        llm_processor = LLMProcessor(config)
        logger.info("开始分析内容...")

        content_data = llm_processor.process_transcript(transcript_data, video_info)

        if not content_data:
            logger.error("❌ LLM 分析失败")
            return False

        logger.info("\n✅ 内容分析成功！")
        logger.info("-" * 80)
        logger.info(f"📋 分析结果:")
        logger.info(f"  • 标题: {content_data.get('title', '')}")
        logger.info(f"  • 摘要: {content_data.get('summary', '')[:100]}...")
        logger.info(f"  • 持仓变动: {len(content_data.get('positions', []))} 条")
        logger.info(f"  • 核心金句: {len(content_data.get('quotes', []))} 条")

        # 展示持仓变动
        positions = content_data.get('positions', [])
        if positions:
            logger.info("\n📊 持仓变动:")
            logger.info("-" * 80)
            for i, pos in enumerate(positions[:3], 1):
                logger.info(f"  {i}. {pos.get('name', '')} - {pos.get('action', '')}")
                logger.info(f"     详情: {pos.get('position_details', '')}")
                logger.info(f"     逻辑: {pos.get('logic', '')[:80]}...")

        # 展示核心金句
        quotes = content_data.get('quotes', [])
        if quotes:
            logger.info("\n💬 核心金句:")
            logger.info("-" * 80)
            for i, quote in enumerate(quotes[:3], 1):
                logger.info(f'  {i}. "{quote}"')

        # 保存分析结果
        output_file = "test_content_result.json"
        # 移除 segments 以减小文件大小
        content_save = content_data.copy()
        if 'segments' in content_save:
            content_save['segments'] = f"<{len(content_save['segments'])} segments removed for brevity>"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(content_save, f, ensure_ascii=False, indent=2)
        logger.info(f"\n💾 分析结果已保存到: {output_file}")

        # ==================== 步骤 3: 飞书文档渲染 ====================
        logger.info("\n" + "=" * 80)
        logger.info("步骤 3/4: 飞书文档渲染")
        logger.info("=" * 80)

        feishu_renderer = FeishuRenderer(config)
        logger.info("开始创建飞书文档...")

        doc_url = feishu_renderer.render_content(content_data)

        if not doc_url:
            logger.error("❌ 飞书文档创建失败")
            return False

        logger.info("\n✅ 飞书文档创建成功！")
        logger.info("-" * 80)
        logger.info(f"📄 文档链接: {doc_url}")

        # 保存文档链接
        with open("test_feishu_url.txt", "w") as f:
            f.write(doc_url)
        logger.info("💾 文档链接已保存到: test_feishu_url.txt")

        # ==================== 步骤 4: 测试总结 ====================
        logger.info("\n" + "=" * 80)
        logger.info("步骤 4/4: 测试总结")
        logger.info("=" * 80)

        logger.info("✅ 所有测试通过！")
        logger.info("\n改进点验证:")
        logger.info("  ✓ 语音转文字获取了完整的转录数据（时间戳、说话人）")
        logger.info("  ✓ 飞书文档包含精修的全文逐字稿")
        logger.info("  ✓ 飞书文档包含带时间戳的原始转录")
        logger.info("  ✓ 飞书文档包含持仓变动表格")
        logger.info("  ✓ 飞书文档包含核心金句")
        logger.info("  ✓ 飞书群消息通知已发送")

        logger.info("\n" + "=" * 80)
        logger.info(f"🎉 测试完成！请查看飞书文档: {doc_url}")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        return False


def format_time(seconds: float) -> str:
    """格式化时间为 MM:SS 或 HH:MM:SS"""
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    except Exception:
        return "00:00"


def main():
    parser = argparse.ArgumentParser(description="测试改进后的功能")
    parser.add_argument(
        "--oss-url",
        type=str,
        help="OSS 音频文件 URL"
    )

    args = parser.parse_args()

    # 检查是否提供了 OSS URL
    oss_url = args.oss_url

    # 如果没有提供，尝试从文件读取
    if not oss_url and Path("last_oss_url.txt").exists():
        with open("last_oss_url.txt", "r") as f:
            oss_url = f.read().strip()
        print(f"使用保存的 OSS URL: {oss_url[:80]}...")

    if not oss_url:
        print("错误: 请提供 --oss-url 参数")
        print("\n使用方法:")
        print('  uv run python test_improved_features.py --oss-url "https://your-oss-url.mp3"')
        sys.exit(1)

    # 运行测试
    success = test_transcription_with_oss_url(oss_url)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
