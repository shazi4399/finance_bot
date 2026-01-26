"""
Manual Pipeline Trigger
手动触发流水线：跳过 Bilibili 下载，直接从本地音频开始测试后续流程
"""
import os
import sys
import time
from datetime import datetime

# 引入核心组件
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.utils.storage import OSSStorage
from src.transcriber.transcriber import AudioTranscriber
from src.llm_processor.llm_processor import LLMProcessor
from src.feishu_renderer.feishu_renderer import FeishuRenderer

def run_manual_test(local_audio_path: str):
    # 1. 初始化配置和日志
    logger = setup_logger(name="manual_test")
    
    if not os.path.exists(local_audio_path):
        logger.error(f"❌ 找不到本地音频文件: {local_audio_path}")
        return

    try:
        config = Config("config.yaml")
        logger.info("✅ 配置加载成功")

        # 2. 模拟视频元数据 (假装是从 B 站抓取的)
        mock_video_info = {
            "bvid": "MANUAL_TEST_001",
            "title": "【手动测试】2026年市场复盘与展望",  # 这个标题会显示在飞书文档里
            "upload_time": datetime.now().strftime("%Y%m%d"),
            "duration": 600, # 假设10分钟
            "url": "https://www.bilibili.com/video/BV_TEST_MOCK"
        }

        # 3. 初始化各组件
        # --- Storage ---
        oss_config = {
            "access_key_id": config.get("aliyun.access_key_id"),
            "access_key_secret": config.get("aliyun.access_key_secret"),
            "oss_endpoint": config.get("aliyun.oss_endpoint"),
            "oss_bucket": config.get("aliyun.oss_bucket"),
            "oss_prefix": "manual_test"
        }
        storage = OSSStorage(oss_config)
        
        # --- Transcriber ---
        transcriber = AudioTranscriber(config)
        
        # --- LLM ---
        llm_processor = LLMProcessor(config)
        
        # --- Feishu ---
        feishu_renderer = FeishuRenderer(config)
        
        logger.info("✅ 所有组件初始化完成，开始执行流水线...")

        # ==========================================
        # Stage 2: 上传到 OSS (跳过下载)
        # ==========================================
        logger.info("🚀 [Stage 2] 开始上传音频到 OSS...")
        oss_url = storage.upload_file(local_audio_path)
        logger.info(f"✅ OSS 上传成功: {oss_url}")

        # ==========================================
        # Stage 3: 阿里云听悟转写
        # ==========================================
        logger.info("🚀 [Stage 3] 开始语音转写 (这可能需要几分钟)...")
        transcript_data = transcriber.transcribe_audio_file(oss_url)
        
        if not transcript_data:
            logger.error("❌ 转写失败，流程终止")
            return
        logger.info(f"✅ 转写完成，获取到 {len(transcript_data.get('sentences', []))} 个句子")

        # ==========================================
        # Stage 4: LLM 深度分析
        # ==========================================
        logger.info("🚀 [Stage 4] 开始 LLM 语义分析...")
        # 构造分析上下文
        analysis_context = mock_video_info.copy()
        # 注意：这里 process_transcript 的调用参数要符合你 llm_processor.py 的定义
        content_data = llm_processor.process_transcript(transcript_data, analysis_context)
        
        if not content_data:
            logger.error("❌ LLM 分析失败，流程终止")
            return
        
        # 打印一下 LLM 的输出，方便调试
        logger.info(f"🧠 LLM 分析结果摘要: {str(content_data)[:200]}...")

        # ==========================================
        # Stage 5: 飞书文档渲染
        # ==========================================
        logger.info("🚀 [Stage 5] 开始生成飞书文档...")
        doc_url = feishu_renderer.render_content(content_data, mock_video_info)
        
        if doc_url:
            logger.info(f"🎉🎉🎉 全流程测试成功！")
            logger.info(f"📄 文档链接: {doc_url}")
        else:
            logger.error("❌ 飞书文档生成失败")

    except Exception as e:
        logger.exception(f"❌ 测试过程中发生异常: {e}")

if __name__ == "__main__":
    # 这里的 'test_audio.mp3' 替换成你实际的文件名
    run_manual_test("BV1UNBKBoE5A.mp3")