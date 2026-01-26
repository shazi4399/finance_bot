#!/usr/bin/env python3
"""测试转录功能"""

import os

import yaml

from src.transcriber.tingwu_client import TingwuClient


def main():
    # 加载配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 初始化听悟客户端
    tingwu_config = {
        "app_key": config.get("tingwu", {}).get("app_key"),
        "access_key_id": config.get("tingwu", {}).get("access_key_id"),
        "access_key_secret": config.get("tingwu", {}).get("access_key_secret"),
        "region": config.get("tingwu", {}).get("region", "cn-shanghai"),
    }

    print(f"Tingwu config: {tingwu_config}")

    client = TingwuClient(tingwu_config)

    # 使用已下载的音频文件
    audio_file = "/tmp/finance_bot/BV1UNBKBoE5A.mp3"

    # 上传到OSS
    oss_config = config.get("aliyun", {})
    import oss2

    auth = oss2.Auth(oss_config.get("access_key_id"), oss_config.get("access_key_secret"))
    bucket = oss2.Bucket(auth, oss_config.get("oss_endpoint"), oss_config.get("oss_bucket"))

    # 上传文件
    object_key = f"test_transcribe/{os.path.basename(audio_file)}"
    bucket.put_object_from_file(object_key, audio_file)
    file_url = (
        f"https://{oss_config.get('oss_bucket')}.{oss_config.get('oss_endpoint').replace('https://', '')}/{object_key}"
    )

    print(f"文件已上传到: {file_url}")

    # 开始转录
    try:
        result = client.transcribe_audio(file_url)
        print(f"转录结果: {result[:500]}...")
    except Exception as e:
        print(f"转录失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
