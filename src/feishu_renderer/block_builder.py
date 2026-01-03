"""Feishu Block structure builder"""

from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger


class BlockBuilder:
    """Build Feishu Block structures from content"""

    def __init__(self):
        """Initialize block builder"""
        self.logger = get_logger()

    def build_blocks(self, content_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build Feishu blocks from content data

        Args:
            content_data: Structured content data

        Returns:
            List of Feishu block dictionaries
        """
        self.logger.info("Building Feishu blocks from content data")

        try:
            blocks = []
            raw_blocks = content_data.get("blocks", [])

            for block_data in raw_blocks:
                block = self._build_single_block(block_data)
                if block:
                    blocks.append(block)

            self.logger.info(f"Built {len(blocks)} Feishu blocks")
            return blocks

        except Exception as e:
            self.logger.error(f"Failed to build blocks: {e}")
            return self._get_fallback_blocks(content_data.get("title", "Document"))

    def _build_single_block(self, block_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build a single Feishu block"""
        block_type = block_data.get("type", "")
        content = block_data.get("content", "")

        if not block_type:
            return None

        try:
            if block_type == "heading_1":
                return self._build_heading_1(content)
            elif block_type == "heading_2":
                return self._build_heading_2(content)
            elif block_type == "heading_3":
                return self._build_heading_3(content)
            elif block_type == "text":
                return self._build_text(content)
            elif block_type == "callout":
                return self._build_callout(content, block_data.get("style", "blue"))
            elif block_type == "bullet":
                return self._build_bullet(content)
            elif block_type == "table":
                return self._build_table(block_data.get("headers", []), block_data.get("rows", []))
            elif block_type == "divider":
                return self._build_divider()
            else:
                self.logger.warning(f"Unknown block type: {block_type}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to build block {block_type}: {e}")
            return None

    def _build_heading_1(self, content: str) -> Dict[str, Any]:
        """Build heading 1 block"""
        return {
            "block_type": 3,  # Heading 1
            "heading1": {"elements": [{"text_run": {"content": content}}]},
        }

    def _build_heading_2(self, content: str) -> Dict[str, Any]:
        """Build heading 2 block"""
        return {
            "block_type": 4,  # Heading 2
            "heading2": {"elements": [{"text_run": {"content": content}}]},
        }

    def _build_heading_3(self, content: str) -> Dict[str, Any]:
        """Build heading 3 block"""
        return {
            "block_type": 5,  # Heading 3
            "heading3": {"elements": [{"text_run": {"content": content}}]},
        }

    def _build_text(self, content: str) -> Dict[str, Any]:
        """Build text block (using Heading 9 as workaround for type 1 limitation)"""
        return {
            "block_type": 11,  # Heading 9
            "heading9": {"elements": [{"text_run": {"content": content}}]},
        }

    def _build_callout(self, content: str, style: str = "blue") -> Dict[str, Any]:
        """Build callout block"""
        # Map style to background color
        style_colors = {
            "blue": 5,
            "green": 2,
            "red": 6,
            "yellow": 3,
            "purple": 4,
            "grey": 1,
        }

        background_color = style_colors.get(style, 5)

        return {
            "block_type": 19,  # Callout
            "callout": {
                "background_color": background_color,
                "elements": [{"text_run": {"content": content}}],
            },
        }

    def _build_bullet(self, content: str) -> Dict[str, Any]:
        """Build bullet point block (using Heading 9 as workaround)"""
        return {
            "block_type": 11,  # Heading 9
            "heading9": {"elements": [{"text_run": {"content": f"• {content}"}}]},
        }

    def _build_table(self, headers: List[str], rows: List[List[str]]) -> Dict[str, Any]:
        """Build table block"""
        if not headers or not rows:
            return None

        row_count = len(rows) + 1  # +1 for header row
        column_count = len(headers)

        return {
            "block_type": 31,  # Table
            "table": {"property": {"row_size": row_count, "column_size": column_count}},
        }

    def _build_divider(self) -> Optional[Dict[str, Any]]:
        """Build divider block (Disabled due to API issues)"""
        return None
        # return {
        #     "block_type": 27,  # Divider
        #     "divider": {}
        # }

    def _get_fallback_blocks(self, title: str) -> List[Dict[str, Any]]:
        """Get fallback blocks when building fails"""
        return [
            {
                "block_type": 3,  # Heading 1
                "heading_1": {"elements": [{"text_run": {"content": title}}]},
            },
            {
                "block_type": 19,  # Callout
                "callout": {
                    "background_color": 6,  # Red
                    "elements": [{"text_run": {"content": "⚠️ 文档生成失败，请检查原始数据。"}}],
                },
            },
        ]

    def build_table_cells(self, headers: List[str], rows: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Build table cell blocks

        Args:
            headers: Table headers
            rows: Table rows data

        Returns:
            List of table cell block dictionaries
        """
        cells = []

        # Header cells
        for header in headers:
            cells.append(
                {
                    "block_type": 1,  # Text
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": header,
                                    "text_style": {"bold": True},
                                }
                            }
                        ]
                    },
                }
            )

        # Data cells
        for row in rows:
            for cell_value in row:
                cells.append(
                    {
                        "block_type": 1,  # Text
                        "text": {"elements": [{"text_run": {"content": str(cell_value)}}]},
                    }
                )

        return cells

    def build_interactive_card(self, title: str, summary: str, doc_url: str, tags: List[str] = None) -> Dict[str, Any]:
        """
        Build interactive card for webhook notification

        Args:
            title: Card title
            summary: Card summary
            doc_url: Document URL
            tags: Optional tags list

        Returns:
            Interactive card dictionary
        """
        card_elements = []

        # Add title and summary
        if title or summary:
            content_text = f"**{title}**\n\n{summary}" if title else summary
            card_elements.append({"tag": "div", "text": {"content": content_text, "tag": "lark_md"}})

        # Add tags if provided
        if tags:
            tag_text = "🏷️ " + " | ".join([f"#{tag}" for tag in tags])
            card_elements.append({"tag": "div", "text": {"content": tag_text, "tag": "lark_md"}})

        # Add action button
        card_elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "查看完整报告", "tag": "plain_text"},
                        "type": "primary",
                        "url": doc_url,
                    }
                ],
            }
        )

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "blue",
                    "title": {"content": "🤖 视频情报已生成", "tag": "plain_text"},
                },
                "elements": card_elements,
            },
        }
