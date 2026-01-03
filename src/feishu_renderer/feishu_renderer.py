"""Main Feishu renderer module"""

from typing import Any, Dict, List, Optional

from src.utils.config import Config
from src.utils.logger import get_logger

from .document_renderer import DocumentRenderer


class FeishuRenderer:
    """Main Feishu renderer class"""

    def __init__(self, config: Config):
        """
        Initialize Feishu renderer

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize document renderer
        self.renderer = DocumentRenderer(config)

    def render_content(self, content_data: Dict[str, Any]) -> Optional[str]:
        """
        Render content to Feishu document and send notification

        Args:
            content_data: Structured content data

        Returns:
            Document URL or None if failed
        """
        return self.renderer.render_and_notify(content_data)

    def create_document(self, content_data: Dict[str, Any]) -> Optional[str]:
        """
        Create Feishu document without notification

        Args:
            content_data: Structured content data

        Returns:
            Document URL or None if failed
        """
        return self.renderer.render_document(content_data)

    def send_notification(self, doc_url: str, content_data: Dict[str, Any]) -> bool:
        """
        Send notification for existing document

        Args:
            doc_url: Document URL
            content_data: Content data for notification

        Returns:
            True if successful, False otherwise
        """
        return self.renderer.send_notification(doc_url, content_data)

    def batch_render(self, content_list: List[Dict[str, Any]]) -> List[str]:
        """
        Render multiple documents

        Args:
            content_list: List of content data dictionaries

        Returns:
            List of document URLs
        """
        return self.renderer.batch_render_documents(content_list)
