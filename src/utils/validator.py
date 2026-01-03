"""Configuration validation utilities"""

import re
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger


class ConfigValidator:
    """Configuration validator"""

    def __init__(self):
        """Initialize configuration validator"""
        self.logger = get_logger()

    def validate_all(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate all configuration sections

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate each section
        errors.extend(self._validate_feishu(config.get("feishu", {})))
        errors.extend(self._validate_aliyun(config.get("aliyun", {})))
        errors.extend(self._validate_dashscope(config.get("dashscope", {})))
        errors.extend(self._validate_tingwu(config.get("tingwu", {})))
        errors.extend(self._validate_monitoring(config.get("monitoring", {})))
        errors.extend(self._validate_storage(config.get("storage", {})))
        errors.extend(self._validate_logging(config.get("logging", {})))

        is_valid = len(errors) == 0

        if is_valid:
            self.logger.info("Configuration validation passed")
        else:
            self.logger.error(f"Configuration validation failed: {errors}")

        return is_valid, errors

    def _validate_feishu(self, feishu_config: Dict[str, Any]) -> List[str]:
        """Validate Feishu configuration"""
        errors = []

        # Check required fields
        if not feishu_config.get("app_id"):
            errors.append("Feishu app_id is required")
        elif not self._validate_app_id(feishu_config["app_id"]):
            errors.append("Feishu app_id format is invalid")

        if not feishu_config.get("app_secret"):
            errors.append("Feishu app_secret is required")
        elif not self._validate_app_secret(feishu_config["app_secret"]):
            errors.append("Feishu app_secret format is invalid")

        # Check optional webhook
        webhook = feishu_config.get("webhook")
        if webhook and not self._validate_webhook_url(webhook):
            errors.append("Feishu webhook URL format is invalid")

        return errors

    def _validate_aliyun(self, aliyun_config: Dict[str, Any]) -> List[str]:
        """Validate Aliyun configuration"""
        errors = []

        # Check required fields
        if not aliyun_config.get("access_key_id"):
            errors.append("Aliyun access_key_id is required")
        elif not self._validate_access_key(aliyun_config["access_key_id"]):
            errors.append("Aliyun access_key_id format is invalid")

        if not aliyun_config.get("access_key_secret"):
            errors.append("Aliyun access_key_secret is required")
        elif not self._validate_access_key(aliyun_config["access_key_secret"]):
            errors.append("Aliyun access_key_secret format is invalid")

        if not aliyun_config.get("oss_endpoint"):
            errors.append("Aliyun oss_endpoint is required")
        elif not self._validate_oss_endpoint(aliyun_config["oss_endpoint"]):
            errors.append("Aliyun oss_endpoint format is invalid")

        if not aliyun_config.get("oss_bucket"):
            errors.append("Aliyun oss_bucket is required")
        elif not self._validate_bucket_name(aliyun_config["oss_bucket"]):
            errors.append("Aliyun oss_bucket format is invalid")

        # Check optional region
        region = aliyun_config.get("region")
        if region and not self._validate_region(region):
            errors.append("Aliyun region format is invalid")

        return errors

    def _validate_dashscope(self, dashscope_config: Dict[str, Any]) -> List[str]:
        """Validate DashScope configuration"""
        errors = []

        # Check required fields
        if not dashscope_config.get("api_key"):
            errors.append("DashScope api_key is required")
        elif not self._validate_api_key(dashscope_config["api_key"]):
            errors.append("DashScope api_key format is invalid")

        # Check optional model
        model = dashscope_config.get("model")
        if model and not self._validate_qwen_model(model):
            errors.append("DashScope model is invalid")

        return errors

    def _validate_tingwu(self, tingwu_config: Dict[str, Any]) -> List[str]:
        """Validate Tingwu configuration"""
        errors = []

        # Check required fields
        if not tingwu_config.get("app_key"):
            errors.append("Tingwu app_key is required")
        elif not self._validate_app_key(tingwu_config["app_key"]):
            errors.append("Tingwu app_key format is invalid")

        return errors

    def _validate_monitoring(self, monitoring_config: Dict[str, Any]) -> List[str]:
        """Validate monitoring configuration"""
        errors = []

        # Check required fields
        if not monitoring_config.get("bilibili_uid"):
            errors.append("Bilibili UID is required")
        elif not self._validate_bilibili_uid(monitoring_config["bilibili_uid"]):
            errors.append("Bilibili UID format is invalid")

        # Check optional fields
        check_interval = monitoring_config.get("check_interval")
        if check_interval is not None and not self._validate_interval(check_interval):
            errors.append("Check interval must be a positive integer")

        max_videos = monitoring_config.get("max_videos_per_check")
        if max_videos is not None and not self._validate_max_videos(max_videos):
            errors.append("Max videos per check must be a positive integer")

        return errors

    def _validate_storage(self, storage_config: Dict[str, Any]) -> List[str]:
        """Validate storage configuration"""
        errors = []

        # Check optional fields
        temp_dir = storage_config.get("temp_dir")
        if temp_dir and not self._validate_temp_dir(temp_dir):
            errors.append("Temp directory path is invalid")

        oss_prefix = storage_config.get("oss_prefix")
        if oss_prefix and not self._validate_oss_prefix(oss_prefix):
            errors.append("OSS prefix format is invalid")

        cleanup_days = storage_config.get("cleanup_after_days")
        if cleanup_days is not None and not self._validate_cleanup_days(cleanup_days):
            errors.append("Cleanup after days must be a positive integer")

        return errors

    def _validate_logging(self, logging_config: Dict[str, Any]) -> List[str]:
        """Validate logging configuration"""
        errors = []

        # Check optional fields
        level = logging_config.get("level")
        if level and not self._validate_log_level(level):
            errors.append("Log level is invalid")

        log_file = logging_config.get("file")
        if log_file and not self._validate_log_file(log_file):
            errors.append("Log file path is invalid")

        return errors

    def _validate_app_id(self, app_id: str) -> bool:
        """Validate Feishu app ID format"""
        return isinstance(app_id, str) and len(app_id) >= 10

    def _validate_app_secret(self, app_secret: str) -> bool:
        """Validate Feishu app secret format"""
        return isinstance(app_secret, str) and len(app_secret) >= 20

    def _validate_webhook_url(self, webhook_url: str) -> bool:
        """Validate webhook URL format"""
        webhook_pattern = r"^https://open\.feishu\.cn/open-apis/bot/v2/hook/[a-f0-9-]+$"
        return bool(re.match(webhook_pattern, webhook_url))

    def _validate_access_key(self, access_key: str) -> bool:
        """Validate Aliyun access key format"""
        return isinstance(access_key, str) and len(access_key) >= 16

    def _validate_oss_endpoint(self, endpoint: str) -> bool:
        """Validate OSS endpoint format"""
        endpoint_pattern = r"^oss-[a-z]+-[a-z0-9]+\.aliyuncs\.com$"
        return bool(re.match(endpoint_pattern, endpoint))

    def _validate_bucket_name(self, bucket_name: str) -> bool:
        """Validate OSS bucket name format"""
        bucket_pattern = r"^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$"
        return bool(re.match(bucket_pattern, bucket_name))

    def _validate_region(self, region: str) -> bool:
        """Validate Aliyun region format"""
        region_pattern = r"^[a-z]+-[a-z0-9]+$"
        return bool(re.match(region_pattern, region))

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key format"""
        return isinstance(api_key, str) and len(api_key) >= 20

    def _validate_qwen_model(self, model: str) -> bool:
        """Validate Qwen model name"""
        valid_models = ["qwen-turbo", "qwen-plus", "qwen-max"]
        return model in valid_models

    def _validate_bilibili_uid(self, uid: str) -> bool:
        """Validate Bilibili UID format"""
        return isinstance(uid, str) and uid.isdigit() and len(uid) >= 5

    def _validate_interval(self, interval: int) -> bool:
        """Validate check interval"""
        return isinstance(interval, int) and interval > 0

    def _validate_max_videos(self, max_videos: int) -> bool:
        """Validate max videos per check"""
        return isinstance(max_videos, int) and max_videos > 0

    def _validate_temp_dir(self, temp_dir: str) -> bool:
        """Validate temp directory path"""
        return isinstance(temp_dir, str) and len(temp_dir) > 0

    def _validate_oss_prefix(self, oss_prefix: str) -> bool:
        """Validate OSS prefix"""
        return isinstance(oss_prefix, str) and len(oss_prefix) > 0

    def _validate_cleanup_days(self, cleanup_days: int) -> bool:
        """Validate cleanup days"""
        return isinstance(cleanup_days, int) and cleanup_days > 0

    def _validate_log_level(self, level: str) -> bool:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        return level.upper() in valid_levels

    def _validate_log_file(self, log_file: str) -> bool:
        """Validate log file path"""
        return isinstance(log_file, str) and len(log_file) > 0
