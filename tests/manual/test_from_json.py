"""
从已转录的JSON文件直接测试LLM分析和飞书文档生成
避免重复上传和转录，节省阿里云额度
"""
import json
import os
from datetime import datetime

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.llm_processor.llm_processor import LLMProcessor
from src.feishu_renderer.feishu_renderer import FeishuRenderer
from src.feishu_renderer.feishu_client import FeishuClient


def send_doc_to_feishu_group(webhook_url: str, doc_url: str, title: str, feishu_client: FeishuClient):
    """发送文档链接到飞书群"""
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📄 新文档已生成"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{title}**\n\n点击下方按钮查看文档详情"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看文档"
                            },
                            "type": "primary",
                            "url": doc_url
                        }
                    ]
                }
            ]
        }
    }

    return feishu_client.send_webhook_message(webhook_url, message)


def test_from_json(json_file_path: str):
    """从JSON文件开始测试完整流程"""
    logger = setup_logger(name="test_from_json")

    if not os.path.exists(json_file_path):
        logger.error(f"❌ 找不到JSON文件: {json_file_path}")
        return

    try:
        # 1. 加载配置
        config = Config("config.yaml")
        logger.info("✅ 配置加载成功")

        # 2. 读取转录JSON文件
        logger.info(f"📖 正在读取转录文件: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        logger.info(f"✅ 转录数据加载成功")

        # 3. 模拟视频元数据
        mock_video_info = {
            "bvid": "TEST_FROM_JSON",
            "title": "【测试】金融市场分析与投资策略",
            "upload_time": datetime.now().strftime("%Y%m%d"),
            "duration": transcript_data.get("Transcription", {}).get("AudioInfo", {}).get("Duration", 0) // 1000,
            "url": "https://www.bilibili.com/video/BV_TEST"
        }

        # 4. 初始化LLM处理器
        logger.info("🚀 [Stage 1] 开始LLM语义分析...")
        llm_processor = LLMProcessor(config)

        # 5. 处理转录数据
        content_data = llm_processor.process_transcript(transcript_data, mock_video_info)

        if not content_data:
            logger.error("❌ LLM分析失败，流程终止")
            return

        logger.info(f"✅ LLM分析完成")
        logger.info(f"📊 分析结果预览: {str(content_data)[:300]}...")

        # 6. 生成飞书文档
        logger.info("🚀 [Stage 2] 开始生成飞书文档...")
        feishu_renderer = FeishuRenderer(config)
        doc_url = feishu_renderer.render_content(content_data, mock_video_info)

        if not doc_url:
            logger.error("❌ 飞书文档生成失败")
            return

        logger.info(f"✅ 飞书文档生成成功")
        logger.info(f"📄 文档链接: {doc_url}")

        # 7. 发送文档到飞书群
        logger.info("🚀 [Stage 3] 发送文档到飞书群...")
        webhook_url = config.get("feishu.webhook")

        if webhook_url:
            # 初始化飞书客户端用于发送webhook
            feishu_config = {
                "app_id": config.get("feishu.app_id"),
                "app_secret": config.get("feishu.app_secret")
            }
            feishu_client = FeishuClient(feishu_config)

            success = send_doc_to_feishu_group(
                webhook_url,
                doc_url,
                mock_video_info["title"],
                feishu_client
            )

            if success:
                logger.info("✅ 文档已成功发送到飞书群")
            else:
                logger.warning("⚠️ 文档发送到飞书群失败")
        else:
            logger.warning("⚠️ 未配置webhook，跳过发送到飞书群")

        # 8. 完成
        logger.info("🎉🎉🎉 测试流程全部完成！")
        logger.info(f"📄 文档链接: {doc_url}")

    except Exception as e:
        logger.exception(f"❌ 测试过程中发生异常: {e}")


if __name__ == "__main__":
    # 使用已转录的JSON文件
    json_file = "debug_tingwu_244014ea20824d1a8e9ff278374759ee.json"
    test_from_json(json_file)
