#!/usr/bin/env python3
"""
阿里云OSS音频通义听悟 V2.0 转录测试与参数调优脚本
适配: alibabacloud_tingwu20230930
"""

import os
import sys
import json
import time
from typing import Dict, Any

# 将当前目录加入路径
sys.path.append(os.getcwd())

try:
    from src.transcriber.tingwu_client import TingwuClient
    from src.utils.config import Config
    from src.utils.logger import get_logger, setup_logger
    from src.utils.retry import APIError
    
    # 引入 V2.0 的模型
    from alibabacloud_tingwu20230930 import models as tingwu_models
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    sys.exit(1)

# 初始化日志
logger = setup_logger(name="tingwu_test", level="INFO")

class TunableTingwuClient(TingwuClient):
    """
    增强版听悟客户端 (V2.0适配版)
    """
    def submit_transcription_task(self, file_url: str, custom_params: Dict[str, Any] = None, **kwargs) -> str:
        self.logger.info(f"正在提交转录任务 (V2.0): {file_url}")
        
        # 默认配置
        param_settings = {
            "diarization_enabled": True,
            "output_level": 1
        }
        if custom_params:
            param_settings.update(custom_params)

        try:
            # 1. 配置输入
            input_config = tingwu_models.CreateTaskRequestInput(
                file_url=file_url,
                source_language="cn",
                task_key=f"test_task_{int(time.time())}"
            )

            # 2. 配置转录参数
            trans_params = tingwu_models.CreateTaskRequestParametersTranscription(
                diarization_enabled=param_settings.get("diarization_enabled"),
                output_level=param_settings.get("output_level")
            )
            
            # 3. 配置智能摘要
            summary_params = tingwu_models.CreateTaskRequestParametersSummarization(
                types=["Paragraph", "Conversational", "Questions", "KeyEvents"]
            )

            # 4. 组装参数
            parameters = tingwu_models.CreateTaskRequestParameters(
                transcription=trans_params,
                summarization=summary_params,
                summarization_enabled=True,
                auto_chapters_enabled=True
            )

            # 5. 创建请求
            request = tingwu_models.CreateTaskRequest(
                app_key=self.app_key,
                type="Offline",
                input=input_config,
                parameters=parameters
            )

            response = self.client.create_task(request)
            task_id = response.body.data.task_id
            self.logger.info(f"✅ 任务提交成功，Task ID: {task_id}")
            return task_id

        except Exception as e:
            self.logger.error(f"提交任务失败: {e}")
            raise APIError(f"Submission failed: {e}")

def run_test_case(client: TunableTingwuClient, url: str, case_name: str, params: dict):
    print(f"\n{'='*20} 开始测试: {case_name} {'='*20}")
    
    try:
        # 1. 提交
        task_id = client.submit_transcription_task(url, custom_params=params)
        
        # 2. 等待
        print("⏳ 等待转录完成...")
        task_data = client.wait_for_completion(task_id)
        
        # 3. 获取并解析结果
        print("📥 正在下载并解析结果...")
        parsed_result = client.get_transcription_result(task_data)
        result_text = parsed_result.get("Text", "")
        summary = parsed_result.get("Summary", "")
        
        # 4. 保存
        output_file = f"result_{case_name}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"=== 转录原文 ===\n{result_text}\n\n")
            f.write(f"=== 智能摘要 ===\n{summary}\n\n")
            f.write(f"=== 章节速览 ===\n{json.dumps(parsed_result.get('Chapters'), ensure_ascii=False, indent=2)}\n")
            
        print(f"✅ 转录完成！结果已保存至: {output_file}")
        print(f"📝 摘要预览:\n{str(summary)[:200]}...")
        return result_text
        
    except Exception as e:
        logger.error(f"❌ 测试用例 {case_name} 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    TARGET_URL = "https://shi-shi-ji-jiu-cai.oss-cn-shanghai.aliyuncs.com/test_transcribe/BV1UNBKBoE5A.mp3?Expires=1768064707&OSSAccessKeyId=TMP.3Ksn5Tcc7n8Wgnqx8rvgh5rTxskRXbXRgoQhsnW33hQ15mfCRqLTphJtbNvGEiEaDuXfPZCqtR33a5waLaTqTipGZp8xak&Signature=FAs0cz3prQ3lA4ZQ5hgHNNdk7RU%3D"
    config = Config()
    app_key = config.get("tingwu.app_key")
    access_key = config.get("aliyun.access_key_id")
    secret_key = config.get("aliyun.access_key_secret")
    region = config.get("aliyun.region")

    if not all([app_key, access_key, secret_key]):
        print("❌ 错误：请检查 config.yaml 配置")
        sys.exit(1)

    print(f"DEBUG: Region=[{region}], AppKey=[{app_key[:6]}******{app_key[-4:]}]")
    
    tingwu_config = {
        "app_key": app_key,
        "access_key_id": access_key,
        "access_key_secret": secret_key,
        "region": region,
    }
    
    try:
        client = TunableTingwuClient(tingwu_config)
        run_test_case(
            client, 
            TARGET_URL, 
            case_name="diarization_mode",
            params={"diarization_enabled": True}
        )
    except Exception as e:
        print(f"❌ 运行失败: {e}")