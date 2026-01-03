"""Feishu document rendering engine"""

from typing import Any, Dict, List, Optional

from src.utils.config import Config
from src.utils.logger import get_logger

from .block_builder import BlockBuilder
from .feishu_client import FeishuClient


class DocumentRenderer:
    """Feishu document rendering engine"""

    def __init__(self, config: Config):
        """
        Initialize document renderer

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize components
        feishu_config = {
            "app_id": config.get("feishu.app_id"),
            "app_secret": config.get("feishu.app_secret"),
        }

        self.client = FeishuClient(feishu_config)
        self.builder = BlockBuilder()

    def render_document(self, content_data: Dict[str, Any]) -> Optional[str]:
        """
        Render content data to Feishu document

        Args:
            content_data: Structured content data

        Returns:
            Document URL or None if failed
        """
        self.logger.info("Rendering Feishu document")

        try:
            # Create document
            title = content_data.get("title", "视频内容分析")
            document_id = self.client.create_document(title)

            # Build blocks
            blocks = self.builder.build_blocks(content_data)

            # Filter out table blocks (they are handled separately)
            non_table_blocks = [b for b in blocks if b.get("block_type") != 31]

            # Add blocks to document
            if non_table_blocks:
                self.client.add_blocks(document_id, non_table_blocks)

            # Handle tables separately
            self._handle_tables(document_id, content_data)

            # Get document URL
            doc_url = self.client.get_document_url(document_id)

            self.logger.info(f"Document rendered successfully: {doc_url}")
            return doc_url

        except Exception as e:
            self.logger.error(f"Failed to render document: {e}")
            return None

    def _handle_tables(self, document_id: str, content_data: Dict[str, Any]):
        """Handle table blocks separately"""
        try:
            raw_blocks = content_data.get("blocks", [])

            for block_data in raw_blocks:
                if block_data.get("type") == "table":
                    headers = block_data.get("headers", [])
                    rows = block_data.get("rows", [])

                    if headers and rows:
                        # Create table
                        table_block_id = self.client.create_table(
                            document_id,
                            len(rows) + 1,  # +1 for header row
                            len(headers),
                        )

                        # Fill table cells
                        self.client.fill_table_cells(document_id, table_block_id, headers, rows)

                        self.logger.info(f"Table rendered with {len(headers)} columns and {len(rows)} rows")

        except Exception as e:
            self.logger.error(f"Failed to handle tables: {e}")

    def send_notification(self, doc_url: str, content_data: Dict[str, Any]) -> bool:
        """
        Send notification via webhook

        Args:
            doc_url: Document URL
            content_data: Content data for notification

        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Sending notification via webhook")

        try:
            # Get webhook URL
            webhook_url = self.config.get("feishu.webhook")
            if not webhook_url:
                self.logger.warning("Webhook URL not configured")
                return False

            # Build notification card
            title = content_data.get("title", "视频内容分析")
            summary = content_data.get("summary", "")
            tags = content_data.get("tags", [])

            # Truncate summary if too long
            if len(summary) > 200:
                summary = summary[:200] + "..."

            card = self.builder.build_interactive_card(title, summary, doc_url, tags)

            # Send notification
            success = self.client.send_webhook_message(webhook_url, card)

            if success:
                self.logger.info("Notification sent successfully")
            else:
                self.logger.error("Failed to send notification")

            return success

        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False

    def render_and_notify(self, content_data: Dict[str, Any]) -> Optional[str]:
        """
        Render document and send notification

        Args:
            content_data: Structured content data

        Returns:
            Document URL or None if failed
        """
        try:
            # Render document
            doc_url = self.render_document(content_data)

            if not doc_url:
                return None

            # Send notification
            self.send_notification(doc_url, content_data)

            return doc_url

        except Exception as e:
            self.logger.error(f"Failed to render and notify: {e}")
            return None

    def update_document(self, document_id: str, content_data: Dict[str, Any]) -> bool:
        """
        Update existing document

        Args:
            document_id: Document ID to update
            content_data: New content data

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Updating document: {document_id}")

        try:
            # Build blocks
            blocks = self.builder.build_blocks(content_data)

            # Add blocks to document
            if blocks:
                self.client.add_blocks(document_id, blocks)

            # Handle tables separately
            self._handle_tables(document_id, content_data)

            self.logger.info(f"Document updated successfully: {document_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update document: {e}")
            return False

    def batch_render_documents(self, content_list: List[Dict[str, Any]]) -> List[str]:
        """
        Render multiple documents

        Args:
            content_list: List of content data dictionaries

        Returns:
            List of document URLs
        """
        self.logger.info(f"Batch rendering {len(content_list)} documents")

        doc_urls = []

        for i, content_data in enumerate(content_list, 1):
            self.logger.info(f"Rendering document {i}/{len(content_list)}")

            try:
                doc_url = self.render_and_notify(content_data)
                if doc_url:
                    doc_urls.append(doc_url)
                else:
                    self.logger.warning(f"Failed to render document {i}")

            except Exception as e:
                self.logger.error(f"Error rendering document {i}: {e}")

        self.logger.info(f"Batch rendering completed: {len(doc_urls)}/{len(content_list)} documents")
        return doc_urls
