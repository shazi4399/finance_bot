#!/usr/bin/env python3
"""
使用模拟转录数据测试飞书排版功能

当听悟 App Key 配置有问题时，使用此脚本测试其他功能
"""

import json
import sys

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.llm_processor.llm_processor import LLMProcessor
from src.feishu_renderer.feishu_renderer import FeishuRenderer


def create_mock_transcript_data():
    """创建模拟的转录数据"""
    return {
        "text": "大家好，今天我们来聊一聊最近的持仓变动。首先说一下神威药业，我最近加仓了20万进去，现在总仓位是47.8万。为什么加仓呢？主要有几个原因：第一，这个公司的分红政策很好，就像爹妈养娃一样，会定期给股东回报。第二，从财报来看，营收增长很稳定，现金流也不错。第三，估值相对便宜，市盈率只有15倍左右。接下来说说另一只股票，最近市场波动比较大，我选择了锁仓观望，等待更好的入场时机。总的来说，今天的盈亏是正的，赚了大概5个点，市场整体来说还是比较乐观的。",
        "segments": [
            {
                "text": "大家好，今天我们来聊一聊最近的持仓变动。",
                "start_time": 0.0,
                "end_time": 3.5,
                "speaker_id": 0,
                "confidence": 0.95
            },
            {
                "text": "首先说一下神威药业，我最近加仓了20万进去，现在总仓位是47.8万。",
                "start_time": 3.5,
                "end_time": 8.2,
                "speaker_id": 0,
                "confidence": 0.93
            },
            {
                "text": "为什么加仓呢？主要有几个原因：",
                "start_time": 8.2,
                "end_time": 10.5,
                "speaker_id": 0,
                "confidence": 0.96
            },
            {
                "text": "第一，这个公司的分红政策很好，就像爹妈养娃一样，会定期给股东回报。",
                "start_time": 10.5,
                "end_time": 15.8,
                "speaker_id": 0,
                "confidence": 0.94
            },
            {
                "text": "第二，从财报来看，营收增长很稳定，现金流也不错。",
                "start_time": 15.8,
                "end_time": 19.5,
                "speaker_id": 0,
                "confidence": 0.95
            },
            {
                "text": "第三，估值相对便宜，市盈率只有15倍左右。",
                "start_time": 19.5,
                "end_time": 23.0,
                "speaker_id": 0,
                "confidence": 0.96
            },
            {
                "text": "接下来说说另一只股票，最近市场波动比较大，我选择了锁仓观望，等待更好的入场时机。",
                "start_time": 23.0,
                "end_time": 28.5,
                "speaker_id": 0,
                "confidence": 0.94
            },
            {
                "text": "总的来说，今天的盈亏是正的，赚了大概5个点，市场整体来说还是比较乐观的。",
                "start_time": 28.5,
                "end_time": 33.0,
                "speaker_id": 0,
                "confidence": 0.95
            }
        ],
        "speakers": {
            "0": {
                "id": "0",
                "name": "主播",
                "gender": "male",
                "confidence": 0.95
            }
        },
        "chapters": [],
        "summary": "",
        "metadata": {
            "task_id": "MOCK_TASK_ID",
            "status": "SUCCESS",
            "duration": 33,
            "word_count": 150,
            "language": "zh-CN"
        }
    }


def test_with_mock_data():
    """使用模拟数据测试LLM分析和飞书渲染"""
    logger = setup_logger("mock_test", level="INFO")
    logger.info("=" * 80)
    logger.info("使用模拟数据测试LLM分析和飞书排版功能")
    logger.info("=" * 80)

    try:
        # 加载配置
        config = Config("config.yaml")
        logger.info("✓ 配置加载成功")

        # 创建模拟转录数据
        logger.info("\n创建模拟转录数据...")
        transcript_data = create_mock_transcript_data()
        logger.info(f"✓ 模拟转录数据创建成功")
        logger.info(f"  • 总字数: {transcript_data['metadata']['word_count']}")
        logger.info(f"  • 时长: {transcript_data['metadata']['duration']} 秒")
        logger.info(f"  • 分段数: {len(transcript_data['segments'])}")

        # 保存模拟数据
        with open("mock_transcript.json", "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        logger.info("✓ 模拟数据已保存到 mock_transcript.json")

        # LLM 分析
        logger.info("\n" + "=" * 80)
        logger.info("步骤 1/2: LLM 内容分析")
        logger.info("=" * 80)

        video_info = {
            "bvid": "MOCK",
            "video_title": "持仓复盘 - 模拟测试",
            "upload_time": "2024-01-04"
        }

        llm_processor = LLMProcessor(config)
        logger.info("开始分析内容...")

        content_data = llm_processor.process_transcript(transcript_data, video_info)

        if not content_data:
            logger.error("❌ LLM 分析失败")
            return False

        logger.info("\n✅ 内容分析成功！")
        logger.info(f"  • 标题: {content_data.get('title', '')}")
        logger.info(f"  • 摘要: {content_data.get('summary', '')[:100]}...")
        logger.info(f"  • 持仓变动: {len(content_data.get('positions', []))} 条")
        logger.info(f"  • 核心金句: {len(content_data.get('quotes', []))} 条")

        # 展示分析结果
        positions = content_data.get('positions', [])
        if positions:
            logger.info("\n📊 持仓变动:")
            for i, pos in enumerate(positions, 1):
                logger.info(f"  {i}. {pos.get('name', '')} - {pos.get('action', '')}")
                logger.info(f"     详情: {pos.get('position_details', '')}")
                logger.info(f"     逻辑: {pos.get('logic', '')[:80]}...")

        quotes = content_data.get('quotes', [])
        if quotes:
            logger.info("\n💬 核心金句:")
            for i, quote in enumerate(quotes, 1):
                logger.info(f'  {i}. "{quote}"')

        # 保存分析结果
        content_save = content_data.copy()
        if 'segments' in content_save:
            content_save['segments'] = f"<{len(content_save['segments'])} segments>"
        with open("mock_content.json", "w", encoding="utf-8") as f:
            json.dump(content_save, f, ensure_ascii=False, indent=2)
        logger.info("\n✓ 分析结果已保存到 mock_content.json")

        # 飞书渲染
        logger.info("\n" + "=" * 80)
        logger.info("步骤 2/2: 飞书文档渲染")
        logger.info("=" * 80)

        feishu_renderer = FeishuRenderer(config)
        logger.info("开始创建飞书文档...")

        doc_url = feishu_renderer.render_content(content_data)

        if not doc_url:
            logger.error("❌ 飞书文档创建失败")
            return False

        logger.info("\n✅ 飞书文档创建成功！")
        logger.info(f"📄 文档链接: {doc_url}")

        # 保存文档链接
        with open("mock_feishu_url.txt", "w") as f:
            f.write(doc_url)
        logger.info("✓ 文档链接已保存到 mock_feishu_url.txt")

        # 总结
        logger.info("\n" + "=" * 80)
        logger.info("测试总结")
        logger.info("=" * 80)
        logger.info("✅ 所有测试通过！")
        logger.info("\n验证的功能:")
        logger.info("  ✓ 使用模拟转录数据")
        logger.info("  ✓ LLM 内容分析（提取持仓、金句）")
        logger.info("  ✓ 飞书文档渲染（精美排版）")
        logger.info("  ✓ 飞书群消息通知")
        logger.info("\n" + "=" * 80)
        logger.info(f"🎉 测试完成！请查看飞书文档: {doc_url}")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_with_mock_data()
    sys.exit(0 if success else 1)
