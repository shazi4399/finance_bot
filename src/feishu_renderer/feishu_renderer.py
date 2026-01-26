import json
from typing import Any, Dict, List, Optional
from src.utils.config import Config
from src.utils.logger import get_logger
from src.feishu_renderer.block_builder import BlockBuilder
from src.feishu_renderer.feishu_client import FeishuClient

class FeishuRenderer:
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger()

        # 使用旧的 FeishuClient
        feishu_config = {
            "app_id": config.get("feishu.app_id"),
            "app_secret": config.get("feishu.app_secret")
        }
        self.client = FeishuClient(feishu_config)
        self.block_builder = BlockBuilder()

    def render_content(self, content_data: Dict[str, Any], video_info: Dict[str, Any] = None) -> Optional[str]:
        """渲染内容到飞书文档"""
        title = "未命名文档"
        if video_info:
            title = video_info.get("video_title") or video_info.get("title") or "未命名复盘"

        try:
            # 1. 创建空文档
            self.logger.info(f"正在创建飞书文档: {title}")
            doc_id = self.client.create_document(title)
            if not doc_id:
                return None

            # 2. 构建内容块
            blocks = self.block_builder.build_blocks(content_data, video_info)
            if not blocks:
                self.logger.warning("⚠️ 警告: 内容数据为空，生成了空文档")
                return self.client.get_document_url(doc_id)

            blocks = self._normalize_blocks(blocks)

            # 调试：打印blocks数量
            self.logger.info(f"生成了 {len(blocks)} 个 blocks")

            # 3. 写入内容 (关键步骤!)
            self.logger.info(f"正在写入 {len(blocks)} 个内容块...")
            success = self.client.add_blocks(doc_id, blocks)

            if not success:
                self.logger.error("❌ 写入内容块失败")
                return None

            # 构造文档链接
            doc_url = self.client.get_document_url(doc_id)

            self.logger.info(f"✅ 飞书文档生成成功: {doc_url}")

            # 发送 Webhook 通知
            webhook_url = self.config.get("feishu.webhook")
            if webhook_url:
                self._send_notification(webhook_url, title, doc_url)
            else:
                self.logger.warning("未配置 feishu.webhook，跳过发送通知")

            return doc_url

        except Exception as e:
            self.logger.error(f"❌ 飞书渲染失败: {e}")
            return None

    def _normalize_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        max_chars = 1500
        normalized: List[Dict[str, Any]] = []

        def split_text(text: str) -> List[str]:
            if text is None:
                return [""]
            text = str(text)
            if len(text) <= max_chars:
                return [text]
            return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

        for block in blocks:
            block_type = block.get("block_type")
            if block_type == 2 and isinstance(block.get("text"), dict):
                elements = block["text"].get("elements", [])
                if elements and isinstance(elements[0], dict) and "text_run" in elements[0]:
                    content = elements[0]["text_run"].get("content", "")
                    for part in split_text(content):
                        normalized.append(
                            {
                                "block_type": 2,
                                "text": {"elements": [{"text_run": {"content": part}}]},
                            }
                        )
                    continue

            if block_type == 12 and isinstance(block.get("bullet"), dict):
                elements = block["bullet"].get("elements", [])
                if elements and isinstance(elements[0], dict) and "text_run" in elements[0]:
                    content = elements[0]["text_run"].get("content", "")
                    for part in split_text(content):
                        normalized.append(
                            {
                                "block_type": 12,
                                "bullet": {"elements": [{"text_run": {"content": part}}]},
                            }
                        )
                    continue

            if isinstance(block_type, int) and 3 <= block_type <= 9:
                level = block_type - 2
                key = f"heading{level}"
                heading = block.get(key)
                if isinstance(heading, dict):
                    elements = heading.get("elements", [])
                    if elements and isinstance(elements[0], dict) and "text_run" in elements[0]:
                        content = elements[0]["text_run"].get("content", "")
                        if isinstance(content, str) and len(content) > max_chars:
                            content = content[:max_chars]
                        normalized.append(
                            {
                                "block_type": block_type,
                                key: {"elements": [{"text_run": {"content": content}}]},
                            }
                        )
                        continue

            normalized.append(block)

        return normalized

    def _send_notification(self, webhook_url: str, title: str, doc_url: str):
        """发送飞书卡片通知"""
        self.logger.info(f"正在发送飞书通知: {title}")
        
        card_content = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "📋 视频复盘文档已生成"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**标题**: {title}\n\n[点击查看文档]({doc_url})"
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "打开文档"
                                },
                                "url": doc_url,
                                "type": "primary"
                            }
                        ]
                    }
                ]
            }
        }
        
        success = self.client.send_webhook_message(webhook_url, card_content)
        if success:
            self.logger.info("✅ 飞书通知发送成功")
        else:
            self.logger.error("❌ 飞书通知发送失败")
