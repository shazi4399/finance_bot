"""Aliyun OSS storage integration"""

import os
import time
from typing import Any, Dict, Optional

import oss2
from oss2.exceptions import OssError

from src.utils.logger import get_logger
from src.utils.retry import NetworkError, with_retry


class OSSStorage:
    """Aliyun OSS storage manager"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OSS storage

        Args:
            config: OSS configuration dictionary
        """
        self.config = config
        self.logger = get_logger()

        # Extract configuration
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.endpoint = config.get("oss_endpoint")
        self.bucket_name = config.get("oss_bucket")
        self.prefix = config.get("oss_prefix", "daily_transcribe")

        # Validate configuration
        if not all(
            [
                self.access_key_id,
                self.access_key_secret,
                self.endpoint,
                self.bucket_name,
            ]
        ):
            raise ValueError("OSS configuration incomplete")

        # Initialize OSS auth and bucket
        try:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

            # Test connection
            self.bucket.get_bucket_info()
            self.logger.info(f"OSS storage initialized: {self.bucket_name}")

        except OssError as e:
            self.logger.error(f"Failed to initialize OSS: {e}")
            raise NetworkError(f"OSS initialization failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, OssError))
    def upload_file(self, local_file_path: str, remote_name: Optional[str] = None) -> str:
        """
        Upload file to OSS with resumable upload

        Args:
            local_file_path: Local file path to upload
            remote_name: Remote file name (auto-generated if None)

        Returns:
            Public URL of uploaded file
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        # Generate remote name if not provided
        if not remote_name:
            filename = os.path.basename(local_file_path)
            timestamp = int(time.time())
            remote_name = f"{self.prefix}/{timestamp}_{filename}"
        else:
            remote_name = f"{self.prefix}/{remote_name}"

        self.logger.info(f"Uploading {local_file_path} to OSS: {remote_name}")

        try:
            # Use resumable upload for large files
            oss2.resumable_upload(
                self.bucket,
                remote_name,
                local_file_path,
                progress_callback=self._upload_progress_callback,
            )

            # Generate presigned URL (valid for 24 hours) to allow access for transcription
            # file_url = f"https://{self.bucket_name}.{self.endpoint}/{remote_name}"
            file_url = self.bucket.sign_url("GET", remote_name, 24 * 3600)

            self.logger.info(f"File uploaded successfully: {file_url}")
            return file_url

        except OssError as e:
            self.logger.error(f"OSS upload failed: {e}")
            raise NetworkError(f"OSS upload failed: {e}")

    def _upload_progress_callback(self, consumed_bytes, total_bytes):
        """Progress callback for upload"""
        if total_bytes:
            progress = (consumed_bytes / total_bytes) * 100
            self.logger.debug(f"Upload progress: {progress:.1f}%")

    @with_retry(max_attempts=3, exceptions=(NetworkError, OssError))
    def generate_presigned_url(self, remote_name: str, expires_in: int = 3600) -> str:
        """
        Generate presigned URL for private file

        Args:
            remote_name: Remote file name
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        try:
            full_remote_name = f"{self.prefix}/{remote_name}"
            url = self.bucket.sign_url("GET", full_remote_name, expires_in)
            self.logger.debug(f"Generated presigned URL for {full_remote_name}")
            return url

        except OssError as e:
            self.logger.error(f"Failed to generate presigned URL: {e}")
            raise NetworkError(f"Presigned URL generation failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, OssError))
    def delete_file(self, remote_name: str):
        """
        Delete file from OSS

        Args:
            remote_name: Remote file name
        """
        try:
            full_remote_name = f"{self.prefix}/{remote_name}"
            self.bucket.delete_object(full_remote_name)
            self.logger.info(f"Deleted file from OSS: {full_remote_name}")

        except OssError as e:
            self.logger.error(f"Failed to delete file: {e}")
            raise NetworkError(f"OSS delete failed: {e}")

    def list_files(self, prefix: Optional[str] = None, max_keys: int = 100) -> list:
        """
        List files in OSS bucket

        Args:
            prefix: Additional prefix to filter files
            max_keys: Maximum number of files to return

        Returns:
            List of file information dictionaries
        """
        try:
            if prefix:
                full_prefix = f"{self.prefix}/{prefix}"
            else:
                full_prefix = self.prefix

            files = []
            for obj in oss2.ObjectIterator(self.bucket, prefix=full_prefix, max_keys=max_keys):
                files.append(
                    {
                        "key": obj.key,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag,
                    }
                )

            self.logger.debug(f"Listed {len(files)} files with prefix {full_prefix}")
            return files

        except OssError as e:
            self.logger.error(f"Failed to list files: {e}")
            return []

    def get_file_info(self, remote_name: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from OSS

        Args:
            remote_name: Remote file name

        Returns:
            File information dictionary or None if not found
        """
        try:
            full_remote_name = f"{self.prefix}/{remote_name}"
            meta = self.bucket.get_object_meta(full_remote_name)

            return {
                "key": full_remote_name,
                "size": int(meta.headers.get("Content-Length", 0)),
                "last_modified": meta.headers.get("Last-Modified"),
                "content_type": meta.headers.get("Content-Type"),
                "etag": meta.headers.get("Etag"),
            }

        except OssError as e:
            if e.status == 404:
                self.logger.debug(f"File not found: {full_remote_name}")
                return None
            else:
                self.logger.error(f"Failed to get file info: {e}")
                return None

    def setup_lifecycle_rule(self, days: int = 1):
        """
        Setup lifecycle rule to automatically delete old files

        Args:
            days: Number of days after which files are deleted
        """
        try:
            rule_id = f"{self.prefix}_cleanup_{days}days"

            lifecycle_rule = oss2.models.LifecycleRule(
                id=rule_id,
                prefix=self.prefix,
                status="Enabled",
                expiration=oss2.models.LifecycleExpiration(days=days),
            )

            # Apply lifecycle rule
            lifecycle = oss2.models.BucketLifecycle([lifecycle_rule])
            self.bucket.put_bucket_lifecycle(lifecycle)

            self.logger.info(f"Setup lifecycle rule: {rule_id} (delete after {days} days)")

        except OssError as e:
            self.logger.error(f"Failed to setup lifecycle rule: {e}")
            raise NetworkError(f"Lifecycle rule setup failed: {e}")

    def get_bucket_info(self) -> Dict[str, Any]:
        """
        Get bucket information

        Returns:
            Bucket information dictionary
        """
        try:
            info = self.bucket.get_bucket_info()
            return {
                "name": info.name,
                "location": info.location,
                "creation_date": info.creation_date,
                "storage_class": info.storage_class,
                "intranet_endpoint": info.intranet_endpoint,
                "internet_endpoint": info.internet_endpoint,
            }

        except OssError as e:
            self.logger.error(f"Failed to get bucket info: {e}")
            return {}
