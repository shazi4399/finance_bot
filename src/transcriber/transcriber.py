"""
Audio Transcriber Service
"""
from typing import Any, Dict, Optional
from src.utils.config import Config
from src.utils.logger import get_logger
from .tingwu_client import TingwuClient

class AudioTranscriber:
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger()
        
        # 传递必要的配置
        # ⚠️ 关键修复：显式传递 tingwu.app_key，防止被过滤掉
        client_config = {
            "aliyun.access_key_id": config.get("aliyun.access_key_id"),
            "aliyun.access_key_secret": config.get("aliyun.access_key_secret"),
            # ✅ 补上这两行，打通数据流
            "tingwu.app_key": config.get("tingwu.app_key"), 
            "aliyun.app_key": config.get("aliyun.app_key") 
        }
        
        self.client = TingwuClient(client_config)

    def transcribe_audio_file(self, file_url: str) -> Optional[Dict[str, Any]]:
        """
        执行转写流程
        """
        self.logger.info(f"开始转写音频: {file_url}")
        
        # 1. 提交任务
        task_id = self.client.submit_task(file_url)
        if not task_id:
            return None
            
        # 2. 等待结果
        result = self.client.get_task_result(task_id)
        if not result:
            return None
            
        # 3. 结果校验
        text_length = len(result.get("full_text", ""))
        self.logger.info(f"转写完成，文本长度: {text_length} 字")
        
        if text_length == 0:
            self.logger.warning("⚠️ 警告: 转写结果为空白! 请检查音频文件是否损坏或静音。")
            
        return result