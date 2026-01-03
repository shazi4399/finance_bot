#!/usr/bin/env python3
"""
验证当前听悟配置和状态
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.utils.config import Config
from src.utils.logger import get_logger


def verify_current_setup():
    """验证当前配置"""
    logger = get_logger()
    logger.info("=== 验证当前听悟配置 ===")

    try:
        config = Config()

        # 检查当前使用的配置
        logger.info("检查配置文件内容:")

        # 听悟配置
        tingwu_app_key = config.get("tingwu.app_key")
        logger.info(f"听悟AppKey: {tingwu_app_key}")

        # 阿里云配置
        aliyun_access_key = config.get("aliyun.access_key_id")
        aliyun_secret = config.get("aliyun.access_key_secret")
        aliyun_region = config.get("aliyun.region")

        logger.info(f"阿里云AccessKey: {aliyun_access_key[:10]}..." if aliyun_access_key else "未配置")
        logger.info(f"阿里云区域: {aliyun_region}")

        # 转录服务配置
        transcription_service = config.get("transcription.service")
        transcription_language = config.get("transcription.language")

        logger.info(f"转录服务: {transcription_service}")
        logger.info(f"转录语言: {transcription_language}")

        # 检查配置是否完整
        required_configs = {
            "tingwu.app_key": tingwu_app_key,
            "aliyun.access_key_id": aliyun_access_key,
            "aliyun.access_key_secret": aliyun_secret,
        }

        missing_configs = [k for k, v in required_configs.items() if not v]

        if missing_configs:
            logger.warning(f"缺失的配置: {missing_configs}")
            return False
        else:
            logger.info("✅ 所有必需配置都已设置")
            return True

    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        return False


def test_tingwu_client_directly():
    """直接测试听悟客户端"""
    logger = get_logger()
    logger.info("=== 直接测试听悟客户端 ===")

    try:
        from src.transcriber.tingwu_client import TingwuClient

        config = Config()

        # 创建听悟配置
        tingwu_config = {
            "app_key": config.get("tingwu.app_key"),
            "access_key_id": config.get("aliyun.access_key_id"),
            "access_key_secret": config.get("aliyun.access_key_secret"),
            "region": config.get("aliyun.region", "cn-shanghai"),
        }

        logger.info("正在初始化听悟客户端...")
        logger.info(f"AppKey: {tingwu_config['app_key']}")
        logger.info(f"区域: {tingwu_config['region']}")

        # 尝试初始化客户端
        TingwuClient(tingwu_config)
        logger.info("✅ 听悟客户端初始化成功")

        return True

    except Exception as e:
        logger.error(f"❌ 听悟客户端初始化失败: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        return False


def test_transcriber_initialization():
    """测试转录器初始化"""
    logger = get_logger()
    logger.info("=== 测试转录器初始化 ===")

    try:
        from src.transcriber.transcriber import AudioTranscriber

        config = Config()

        logger.info("正在初始化音频转录器...")
        transcriber = AudioTranscriber(config)
        logger.info("✅ 音频转录器初始化成功")

        # 检查客户端类型
        client_type = type(transcriber.client).__name__
        logger.info(f"使用的客户端类型: {client_type}")

        if client_type == "TingwuClient":
            logger.info("✅ 正在使用通义听悟客户端")
            return True
        else:
            logger.warning(f"使用的是 {client_type}，不是预期的 TingwuClient")
            return False

    except Exception as e:
        logger.error(f"❌ 转录器初始化失败: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    print("=== 通义听悟配置验证 ===")

    tests = [
        ("配置验证", verify_current_setup),
        ("听悟客户端初始化", test_tingwu_client_directly),
        ("转录器初始化", test_transcriber_initialization),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅ 通过' if result else '❌ 失败'}: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results.append((test_name, False))

    print("\n=== 总结 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        print(f"{'✅' if result else '❌'} {test_name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 通义听悟配置完全正确！")
    else:
        print("❌ 部分测试失败，需要检查配置")

    sys.exit(0 if passed == total else 1)
