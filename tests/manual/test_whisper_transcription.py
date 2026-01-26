#!/usr/bin/env python3
"""测试使用Whisper进行转录"""

import os

from src.utils.logger import get_logger


def main():
    # 初始化日志
    get_logger()

    # 使用已下载的音频文件
    audio_file = "/tmp/finance_bot/BV1UNBKBoE5A.mp3"

    print(f"开始转录文件: {audio_file}")

    try:
        # 尝试使用openai-whisper
        import whisper

        # 加载模型
        model = whisper.load_model("base")

        # 转录音频
        result = model.transcribe(audio_file, language="zh")

        transcription = result["text"]
        print(f"转录成功: {transcription[:500]}...")

        # 保存转录结果
        with open("transcription_result.txt", "w", encoding="utf-8") as f:
            f.write(transcription)

        print("转录结果已保存到 transcription_result.txt")

    except ImportError:
        print("未安装openai-whisper，尝试安装...")
        os.system("pip install openai-whisper")
        print("请重新运行此脚本")
    except Exception as e:
        print(f"转录出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
