#!/usr/bin/env python3
"""测试使用通义千问进行转录"""

import os

import requests
import yaml

from src.utils.logger import get_logger


def main():
    # 加载配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 初始化日志
    logger = get_logger()

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

    # 使用通义千问API进行转录
    api_key = config.get("dashscope", {}).get("api_key")

    # 准备请求数据
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": "paraformer-v1",
        "input": {"file_urls": [file_url]},
        "parameters": {
            "format": "mp3",
            "sample_rate": 16000,
            "language": "zh-CN",
            "phrase_id": "finance-phrases",  # 金融领域短语增强
        },
    }

    print("开始转录...")
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if result.get("output") and result["output"].get("text"):
            transcription = result["output"]["text"]
            print(f"转录成功: {transcription[:500]}...")
        else:
            print(f"转录失败: {result}")

    except Exception as e:
        if "response" in locals():
            print(f"Error Response: {response.text}")
        print(f"转录出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
