#!/usr/bin/env python3
"""测试完整的处理流程"""

import os

from src.pipeline import ContentIntelligencePipeline
from src.utils.config import Config
from src.utils.logger import get_logger


def main():
    # 初始化日志
    get_logger()

    # 加载配置
    config = Config("config.yaml")

    # 初始化管道
    pipeline = ContentIntelligencePipeline(config)

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

    # 手动处理视频
    video_info = {
        "bvid": "BV1UNBKBoE5A",
        "title": "第1089日投资记录:侥幸微赚，略微减仓消费加仓中药。",
        "upload_time": "20241224",
        "url": "https://www.bilibili.com/video/BV1UNBKBoE5A",
    }

    # 处理视频
    try:
        result = pipeline._process_video(video_info)
        print(f"处理成功: {result}")
    except Exception as e:
        print(f"处理失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
