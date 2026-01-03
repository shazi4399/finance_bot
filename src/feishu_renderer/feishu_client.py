"""Feishu API client for document operations"""

import json
import time
from typing import Any, Dict, List

import requests

from src.utils.logger import get_logger
from src.utils.retry import APIError, NetworkError, with_retry


class FeishuClient:
    """Feishu API client"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Feishu client

        Args:
            config: Feishu configuration dictionary
        """
        self.config = config
        self.logger = get_logger()

        # Extract configuration
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")

        # Validate configuration
        if not all([self.app_id, self.app_secret]):
            raise ValueError("Feishu configuration incomplete")

        # API endpoints
        self.base_url = "https://open.feishu.cn/open-apis"
        self.token_url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        self.doc_url = f"{self.base_url}/docx/v1/documents"

        # Initialize token
        self._access_token = None
        self._token_expires_at = 0

        self.logger.info("Feishu client initialized")

    def _get_access_token(self) -> str:
        """Get or refresh access token"""
        current_time = time.time()

        # Check if token is still valid
        if self._access_token and current_time < self._token_expires_at:
            return self._access_token

        # Request new token
        try:
            response = requests.post(
                self.token_url,
                json={"app_id": self.app_id, "app_secret": self.app_secret},
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise APIError(f"Feishu API error: {data.get('msg', 'Unknown error')}")

            self._access_token = data.get("tenant_access_token")
            # Set token to expire 5 minutes before actual expiry
            self._token_expires_at = current_time + data.get("expire", 7200) - 300

            self.logger.debug("Feishu access token refreshed")
            return self._access_token

        except requests.RequestException as e:
            self.logger.error(f"Failed to get Feishu access token: {e}")
            raise NetworkError(f"Feishu authentication failed: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization"""
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def create_document(self, title: str = "Untitled Document") -> str:
        """
        Create a new Feishu document

        Args:
            title: Document title

        Returns:
            Document ID
        """
        self.logger.info(f"Creating Feishu document: {title}")

        try:
            response = requests.post(self.doc_url, headers=self._get_headers(), json={"title": title})

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise APIError(f"Feishu API error: {data.get('msg', 'Unknown error')}")

            document_id = data.get("data", {}).get("document", {}).get("document_id")
            if not document_id:
                raise APIError("No document ID in response")

            self.logger.info(f"Document created: {document_id}")
            return document_id

        except requests.RequestException as e:
            self.logger.error(f"Failed to create document: {e}")
            raise NetworkError(f"Document creation failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def add_blocks(self, document_id: str, blocks: List[Dict[str, Any]], index: int = -1) -> bool:
        """
        Add blocks to document

        Args:
            document_id: Document ID
            blocks: List of block dictionaries
            index: Insert position (-1 for end)

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Adding {len(blocks)} blocks to document: {document_id}")

        try:
            url = f"{self.doc_url}/{document_id}/blocks/{document_id}/children"

            payload = {"children": blocks, "index": index}

            response = requests.post(url, headers=self._get_headers(), json=payload)

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise APIError(f"Feishu API error: {data.get('msg', 'Unknown error')}")

            self.logger.info(f"Blocks added successfully to document: {document_id}")
            return True

        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                self.logger.error(f"Feishu API Error Response: {e.response.text}")
            self.logger.error(f"Failed to add blocks: {e}")
            self.logger.error(f"Payload was: {json.dumps(payload, ensure_ascii=False)}")
            raise NetworkError(f"Block addition failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def create_table(self, document_id: str, rows: int, columns: int) -> str:
        """
        Create a table block

        Args:
            document_id: Document ID
            rows: Number of rows
            columns: Number of columns

        Returns:
            Table block ID
        """
        self.logger.info(f"Creating table {rows}x{columns} in document: {document_id}")

        try:
            url = f"{self.doc_url}/{document_id}/blocks/{document_id}/children"

            table_block = {
                "block_type": 31,  # Table block type
                "table": {"property": {"row_size": rows, "column_size": columns}},
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                json={"children": [table_block], "index": -1},
            )

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise APIError(f"Feishu API error: {data.get('msg', 'Unknown error')}")

            # Extract table block ID from response
            children = data.get("data", {}).get("children", [])
            if not children:
                raise APIError("No children in response")

            table_block_id = children[0].get("block_id")
            if not table_block_id:
                raise APIError("No table block ID in response")

            self.logger.info(f"Table created with block ID: {table_block_id}")
            return table_block_id

        except requests.RequestException as e:
            self.logger.error(f"Failed to create table: {e}")
            raise NetworkError(f"Table creation failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def fill_table_cells(
        self,
        document_id: str,
        table_block_id: str,
        headers: List[str],
        rows: List[List[str]],
    ) -> bool:
        """
        Fill table cells with data

        Args:
            document_id: Document ID
            table_block_id: Table block ID
            headers: Table headers
            rows: Table rows data

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Filling table cells for table: {table_block_id}")

        try:
            # First, get table cell IDs
            table_info = self.get_block_info(document_id, table_block_id)
            self.logger.debug(f"Table info: {json.dumps(table_info)}")
            cell_ids = table_info.get("table", {}).get("cells", [])
            if not cell_ids:
                # Fallback to children if cells not found
                cell_ids = table_info.get("children", [])

            if not cell_ids:
                self.logger.error(f"Table info has no cells: {table_info}")
                raise APIError("No table cell IDs found")

            # Fill header row
            for i, header in enumerate(headers):
                if i < len(cell_ids):
                    cell_id = cell_ids[i]
                    self._fill_cell(document_id, cell_id, header)
                    time.sleep(0.2)  # Rate limiting

            # Fill data rows
            for row_idx, row in enumerate(rows):
                for col_idx, cell_value in enumerate(row):
                    cell_index = (row_idx + 1) * len(headers) + col_idx  # +1 for header row
                    if cell_index < len(cell_ids):
                        cell_id = cell_ids[cell_index]
                        self._fill_cell(document_id, cell_id, cell_value)
                        time.sleep(0.2)  # Rate limiting

            self.logger.info("Table cells filled successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to fill table cells: {e}")
            return False

    def _fill_cell(self, document_id: str, cell_id: str, content: str):
        """Fill a single table cell"""
        try:
            url = f"{self.doc_url}/{document_id}/blocks/{cell_id}/children"

            text_block = {
                "block_type": 11,  # Heading 9 (Workaround for Text block limitation)
                "heading9": {"elements": [{"text_run": {"content": str(content)}}]},
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                json={"children": [text_block], "index": -1},
            )

            response.raise_for_status()

        except requests.RequestException as e:
            self.logger.error(f"Failed to fill cell {cell_id}: {e}")
            raise

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def get_block_info(self, document_id: str, block_id: str) -> Dict[str, Any]:
        """
        Get block information

        Args:
            document_id: Document ID
            block_id: Block ID

        Returns:
            Block information dictionary
        """
        try:
            url = f"{self.doc_url}/{document_id}/blocks/{block_id}"

            response = requests.get(url, headers=self._get_headers())

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise APIError(f"Feishu API error: {data.get('msg', 'Unknown error')}")

            return data.get("data", {}).get("block", {})

        except requests.RequestException as e:
            self.logger.error(f"Failed to get block info: {e}")
            raise NetworkError(f"Block info retrieval failed: {e}")

    def get_document_url(self, document_id: str) -> str:
        """
        Get document URL

        Args:
            document_id: Document ID

        Returns:
            Document URL
        """
        return f"https://feishu.cn/docx/{document_id}"

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def send_webhook_message(self, webhook_url: str, message: Dict[str, Any]) -> bool:
        """
        Send message via webhook

        Args:
            webhook_url: Webhook URL
            message: Message payload

        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Sending webhook message")

        try:
            response = requests.post(webhook_url, json=message, headers={"Content-Type": "application/json"})

            response.raise_for_status()

            self.logger.info("Webhook message sent successfully")
            return True

        except requests.RequestException as e:
            self.logger.error(f"Failed to send webhook message: {e}")
            return False
