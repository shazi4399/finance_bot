#!/usr/bin/env python3
"""
测试通义听悟客户端功能
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.transcriber.tingwu_client import TingwuClient
from src.transcriber.transcriber import AudioTranscriber
from src.utils.config import Config
from src.utils.logger import get_logger


def test_tingwu_client():
    """测试听悟客户端基本功能"""
    logger = get_logger()
    logger.info("开始测试通义听悟客户端...")

    try:
        # 加载配置
        config = Config()
        logger.info("配置加载成功")

        # 检查听悟配置
        tingwu_config = {
            "app_key": config.get("tingwu.app_key"),
            "access_key_id": config.get("aliyun.access_key_id"),
            "access_key_secret": config.get("aliyun.access_key_secret"),
            "region": config.get("aliyun.region", "cn-shanghai"),
        }

        # 验证配置完整性
        required_keys = ["app_key", "access_key_id", "access_key_secret"]
        missing_keys = [key for key in required_keys if not tingwu_config.get(key)]

        if missing_keys:
            logger.error(f"配置缺失: {missing_keys}")
            return False

        logger.info(f"听悟配置检查通过: app_key={tingwu_config['app_key'][:10]}...")

        # 初始化听悟客户端
        TingwuClient(tingwu_config)
        logger.info("听悟客户端初始化成功")

        # 测试转录器
        AudioTranscriber(config)
        logger.info("音频转录器初始化成功")

        logger.info("✅ 通义听悟客户端测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def test_configuration():
    """测试配置是否正确"""
    logger = get_logger()
    logger.info("开始测试配置...")

    try:
        config = Config()

        # 检查听悟相关配置
        tingwu_app_key = config.get("tingwu.app_key")
        aliyun_access_key = config.get("aliyun.access_key_id")
        config.get("aliyun.access_key_secret")
        aliyun_region = config.get("aliyun.region")

        logger.info(f"听悟AppKey: {tingwu_app_key[:10] if tingwu_app_key else '未配置'}")
        logger.info(f"阿里云AccessKey: {aliyun_access_key[:10] if aliyun_access_key else '未配置'}")
        logger.info(f"阿里云区域: {aliyun_region}")

        # 检查转录服务配置
        transcription_service = config.get("transcription.service")
        transcription_language = config.get("transcription.language")

        logger.info(f"转录服务: {transcription_service}")
        logger.info(f"转录语言: {transcription_language}")

        if transcription_service != "tingwu":
            logger.warning(f"转录服务配置为 {transcription_service}，但代码已切换到听悟")

        logger.info("✅ 配置测试通过")
        return True

    except Exception as e:
        logger.error(f"❌ 配置测试失败: {e}")
        return False


if __name__ == "__main__":
    print("=== 通义听悟功能测试 ===")

    # 测试配置
    config_ok = test_configuration()

    # 测试客户端
    client_ok = test_tingwu_client()

    if config_ok and client_ok:
        print("\n🎉 所有测试通过！通义听悟功能就绪")
        sys.exit(0)
    else:
        print("\n❌ 测试失败，请检查配置和日志")
        sys.exit(1)
