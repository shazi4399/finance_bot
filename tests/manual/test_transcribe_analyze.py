#!/usr/bin/env python3
"""测试转录和分析功能"""

import os

from src.llm_processor.llm_processor import LLMProcessor
from src.transcriber.whisper_transcriber import WhisperTranscriber
from src.utils.config import Config
from src.utils.logger import get_logger


def main():
    # 初始化日志
    get_logger()

    # 加载配置
    config = Config("config.yaml")

    # 初始化转录器
    whisper_config = {"model_name": config.get("transcription.model", "base")}
    transcriber = WhisperTranscriber(whisper_config)

    # 初始化LLM处理器
    {
        "dashscope.api_key": config.get("dashscope.api_key"),
        "llm.model": config.get("llm.model", "qwen-max"),
    }
    llm_processor = LLMProcessor(config)

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

    # 转录音频
    try:
        print("开始转录...")
        transcription = transcriber.transcribe_local_file(audio_file)
        print(f"转录成功: {transcription[:200]}...")

        # 准备视频信息
        video_info = {
            "bvid": "BV1UNBKBoE5A",
            "title": "第1089日投资记录:侥幸微赚，略微减仓消费加仓中药。",
            "upload_time": "20241224",
            "url": "https://www.bilibili.com/video/BV1UNBKBoE5A",
        }

        # 准备转录数据（使用前1000个字符以避免内容审核问题）
        short_transcription = transcription[:1000]
        transcript_data = {
            "text": short_transcription,
            "metadata": {
                "word_count": len(short_transcription),
                "video_info": video_info,
            },
        }

        # 分析内容
        print("开始分析内容...")
        content_data = llm_processor.process_transcript(transcript_data, video_info)
        print(f"分析成功: {content_data}")

    except Exception as e:
        print(f"处理失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
