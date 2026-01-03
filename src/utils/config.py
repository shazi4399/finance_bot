"""Configuration management for Content Intelligence Pipeline"""

import os
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager with environment variable support"""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file and environment variables"""
        load_dotenv()  # Load .env file if exists

        self.config_path = config_path
        self._config = self._load_config()
        self._override_with_env()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")

    def _override_with_env(self):
        """Override config values with environment variables"""
        env_mappings = {
            "FEISHU_APP_ID": ["feishu", "app_id"],
            "FEISHU_APP_SECRET": ["feishu", "app_secret"],
            "FEISHU_WEBHOOK": ["feishu", "webhook"],
            "ALIYUN_ACCESS_KEY_ID": ["aliyun", "access_key_id"],
            "ALIYUN_ACCESS_KEY_SECRET": ["aliyun", "access_key_secret"],
            "OSS_BUCKET": ["aliyun", "oss_bucket"],
            "DASHSCOPE_API_KEY": ["dashscope", "api_key"],
            "TINGWU_APP_KEY": ["tingwu", "app_key"],
            "BILIBILI_UID": ["monitoring", "bilibili_uid"],
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_value(config_path, env_value)

    def _set_nested_value(self, path: list, value: str):
        """Set nested configuration value"""
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def get(self, key_path: str, default=None):
        """Get configuration value by dot-separated path"""
        keys = key_path.split(".")
        current = self._config

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def validate_required(self) -> bool:
        """Validate that all required configuration values are present"""
        required_keys = [
            "feishu.app_id",
            "feishu.app_secret",
            "aliyun.access_key_id",
            "aliyun.access_key_secret",
            "aliyun.oss_bucket",
            "dashscope.api_key",
            "monitoring.bilibili_uid",
        ]

        missing_keys = []
        for key in required_keys:
            if self.get(key) is None or self.get(key).startswith("<<<<"):
                missing_keys.append(key)

        if missing_keys:
            print(f"Missing required configuration: {', '.join(missing_keys)}")
            return False

        return True

    @property
    def raw(self) -> Dict[str, Any]:
        """Get raw configuration dictionary"""
        return self._config.copy()
