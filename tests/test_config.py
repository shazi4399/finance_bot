"""Test configuration validation"""

import os
import sys
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.utils.validator import ConfigValidator


class TestConfigValidator(unittest.TestCase):
    """Test configuration validator"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = ConfigValidator()

    def test_validate_feishu_config(self):
        """Test Feishu configuration validation"""
        # Valid config
        valid_config = {
            "app_id": "cli_1234567890abcdef",
            "app_secret": "abcdefghijklmnopqrstuvwxyz123456",
            "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/12345678-1234-1234-1234-123456789012",
        }

        is_valid, errors = self.validator._validate_feishu(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid config - missing app_id
        invalid_config = {"app_secret": "abcdefghijklmnopqrstuvwxyz123456"}

        is_valid, errors = self.validator._validate_feishu(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_validate_aliyun_config(self):
        """Test Aliyun configuration validation"""
        # Valid config
        valid_config = {
            "access_key_id": "LTAI12345678901234",
            "access_key_secret": "abcdefghijklmnopqrstuvwxyz1234567890",
            "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "oss_bucket": "test-bucket-name",
            "region": "cn-shanghai",
        }

        is_valid, errors = self.validator._validate_aliyun(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid config - missing access_key_id
        invalid_config = {
            "access_key_secret": "abcdefghijklmnopqrstuvwxyz1234567890",
            "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "oss_bucket": "test-bucket-name",
        }

        is_valid, errors = self.validator._validate_aliyun(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_validate_monitoring_config(self):
        """Test monitoring configuration validation"""
        # Valid config
        valid_config = {
            "bilibili_uid": "123456789",
            "check_interval": 3600,
            "max_videos_per_check": 5,
        }

        is_valid, errors = self.validator._validate_monitoring(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid config - missing bilibili_uid
        invalid_config = {"check_interval": 3600, "max_videos_per_check": 5}

        is_valid, errors = self.validator._validate_monitoring(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_validate_all(self):
        """Test complete configuration validation"""
        # Valid complete config
        valid_config = {
            "feishu": {
                "app_id": "cli_1234567890abcdef",
                "app_secret": "abcdefghijklmnopqrstuvwxyz123456",
            },
            "aliyun": {
                "access_key_id": "LTAI12345678901234",
                "access_key_secret": "abcdefghijklmnopqrstuvwxyz1234567890",
                "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
                "oss_bucket": "test-bucket-name",
            },
            "dashscope": {
                "api_key": "sk-abcdefghijklmnopqrstuvwxyz123456",
                "model": "qwen-max",
            },
            "tingwu": {"app_key": "abcdefghijklmnopqrstuvwxyz123456"},
            "monitoring": {"bilibili_uid": "123456789"},
        }

        is_valid, errors = self.validator.validate_all(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid complete config - missing required fields
        invalid_config = {
            "feishu": {
                "app_id": "cli_1234567890abcdef"
                # Missing app_secret
            },
            "aliyun": {
                "access_key_id": "LTAI12345678901234"
                # Missing other required fields
            },
            # Missing other sections
        }

        is_valid, errors = self.validator.validate_all(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
