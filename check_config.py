#!/usr/bin/env python3
"""
Check configuration and component health
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import Config
from src.utils.logger import get_logger


def check_config():
    """Check configuration completeness"""
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("Configuration Health Check")
    logger.info("=" * 60)

    try:
        config = Config("config.yaml")

        # Check required fields
        required_fields = [
            ("tingwu.app_key", "听悟 App Key"),
            ("aliyun.access_key_id", "阿里云 Access Key ID"),
            ("aliyun.access_key_secret", "阿里云 Access Key Secret"),
            ("aliyun.oss_bucket", "OSS Bucket"),
            ("aliyun.oss_endpoint", "OSS Endpoint"),
            ("feishu.app_id", "飞书 App ID"),
            ("feishu.app_secret", "飞书 App Secret"),
            ("feishu.webhook", "飞书 Webhook"),
            ("dashscope.api_key", "通义千问 API Key"),
        ]

        all_ok = True
        for field, name in required_fields:
            value = config.get(field)
            if value and value != "***" and value != "****":
                logger.info(f"✓ {name}: Configured")
            else:
                logger.error(f"✗ {name}: Not configured or masked")
                all_ok = False

        if all_ok:
            logger.info("\n✅ All required configurations are present!")
            logger.info("\nYou can now run the test with:")
            logger.info("  # Full test (download + transcribe + feishu)")
            logger.info("  python test_pipeline.py --mode full --bvid BV1xx411c7mD")
            logger.info("\n  # Quick test (use existing OSS URL)")
            logger.info("  python test_pipeline.py --mode quick --oss-url 'https://...'")
            return True
        else:
            logger.error("\n❌ Configuration incomplete. Please update config.yaml")
            return False

    except Exception as e:
        logger.error(f"Configuration check failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    if check_config():
        sys.exit(0)
    else:
        sys.exit(1)
