"""
阿里云通义听悟 V2.0 客户端封装 (alibabacloud_tingwu20230930)
已集成：全文转写、区分说话人、智能摘要、章节速览、自动问答
修复：增强转录文本解析能力 (加入递归搜索)
"""

import json
import time
import requests
from typing import Any, Dict, List, Optional

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tingwu20230930.client import Client as Tingwu2Client
from alibabacloud_tingwu20230930 import models as tingwu_models

from src.utils.logger import get_logger
from src.utils.retry import APIError, NetworkError, with_retry

class TingwuClient:
    """阿里云通义听悟 API V2.0 客户端"""

    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.app_key = config.get("app_key")
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.region = config.get("region", "cn-shanghai")
        self.logger = get_logger()

        if not all([self.access_key_id, self.access_key_secret]):
            raise ValueError("Tingwu configuration incomplete: missing AccessKey")

        try:
            client_config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret,
            )
            client_config.endpoint = f"tingwu.{self.region}.aliyuncs.com"
            
            self.client = Tingwu2Client(client_config)
            self.logger.info(f"✅ 通义听悟 V2.0 客户端初始化成功 (Region: {self.region})")

        except Exception as e:
            self.logger.error(f"Failed to initialize Tingwu V2 client: {e}")
            raise NetworkError(f"Client initialization failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def submit_transcription_task(self, file_url: str, **kwargs) -> str:
        """提交转录任务 (V2.0)"""
        self.logger.info(f"Submitting transcription task (V2.0) for: {file_url}")

        try:
            input_config = tingwu_models.CreateTaskRequestInput(
                file_url=file_url,
                source_language="cn",
                task_key=f"task_{int(time.time())}"
            )

            transcription = tingwu_models.CreateTaskRequestParametersTranscription(
                diarization_enabled=True,
                output_level=1
            )

            summarization = tingwu_models.CreateTaskRequestParametersSummarization(
                types=["Paragraph", "Conversational", "Questions", "KeyEvents", "Actions"]
            )

            parameters = tingwu_models.CreateTaskRequestParameters(
                transcription=transcription,
                summarization=summarization,
                summarization_enabled=True,
                auto_chapters_enabled=True
            )

            request = tingwu_models.CreateTaskRequest(
                app_key=self.app_key,
                type="Offline",
                input=input_config,
                parameters=parameters
            )

            response = self.client.create_task(request)
            
            if response.status_code != 200 or not response.body.data:
                raise APIError(f"Task submission failed: {response}")

            task_id = response.body.data.task_id
            self.logger.info(f"Transcription task submitted: {task_id}")
            return task_id

        except Exception as e:
            self.logger.error(f"Failed to submit task: {e}")
            raise APIError(f"Submission failed: {e}")

    def wait_for_completion(self, task_id: str, timeout: int = 3600, poll_interval: int = 10) -> Dict[str, Any]:
        """轮询等待任务完成"""
        self.logger.info(f"Waiting for task: {task_id}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = self.client.get_task_info(task_id)
                status_data = response.body.data
                task_status = status_data.task_status
                
                if task_status == "COMPLETED":
                    self.logger.info(f"Task {task_id} completed successfully")
                    return status_data
                elif task_status == "FAILED":
                    err_msg = status_data.error_message
                    raise APIError(f"Task failed: {err_msg}")

                self.logger.debug(f"Status: {task_status}, waiting...")
                time.sleep(poll_interval)

            except Exception as e:
                if "failed" in str(e).lower() and "Task failed" not in str(e):
                    self.logger.warning(f"Check status failed, retrying: {e}")
                    time.sleep(poll_interval)
                else:
                    raise e

        raise APIError("Task timed out")

    def get_transcription_result(self, task_data: Any) -> Dict[str, Any]:
        """
        从完成的任务数据中提取结果 (修复版)
        """
        result = task_data.result
        final_result = {
            "Text": "",
            "Summary": "",
            "Chapters": [],
            "Questions": []
        }

        # 1. 获取转录文本 (Transcription)
        if result and hasattr(result, 'transcription') and result.transcription:
            try:
                self.logger.info(f"Downloading transcription from: {result.transcription}")
                data = self._download_json(result.transcription)
                
                # --- 核心修复：多策略解析文本 ---
                full_text = []
                
                # 策略A: 标准路径 (Transcription -> Paragraphs)
                trans_source = data.get('Transcription', data)
                paragraphs = trans_source.get('Paragraphs', [])
                
                for p in paragraphs:
                    text = p.get('Text')
                    if not text and 'Sentences' in p:
                        text = "".join([s.get('Text', '') for s in p['Sentences']])
                    if text:
                        full_text.append(text)
                
                # 策略B: 暴力搜索 (如果策略A失败)
                if not full_text:
                    self.logger.warning("标准路径未提取到文本，启动深度搜索...")
                    full_text = self._recursive_find_text(data)
                
                final_result["Text"] = "\n".join(full_text)
                self.logger.info(f"成功提取转录文本: {len(final_result['Text'])} 字符")

            except Exception as e:
                self.logger.error(f"Failed to download/parse transcription: {e}")

        # 2. 获取 AI 摘要 (Summarization)
        if result and hasattr(result, 'summarization') and result.summarization:
            try:
                self.logger.info(f"Downloading summary from: {result.summarization}")
                data = self._download_json(result.summarization)
                summ_source = data.get('Summarization', data)

                if 'ParagraphSummary' in summ_source:
                    final_result["Summary"] = summ_source['ParagraphSummary']
                
                if 'ConversationalSummary' in summ_source:
                    final_result["Chapters"] = [
                        {
                            "Title": item.get('Headline', ''), 
                            "Summary": item.get('Summary', ''), 
                            "Start": item.get('Start'), 
                            "End": item.get('End')
                        }
                        for item in summ_source['ConversationalSummary']
                    ]
                
                if 'Questions' in summ_source:
                    final_result["Questions"] = summ_source['Questions']
                    
            except Exception as e:
                self.logger.error(f"Failed to download/parse summary: {e}")

        return final_result

    def _recursive_find_text(self, obj: Any) -> List[str]:
        """辅助方法：递归查找所有 Text 字段"""
        texts = []
        if isinstance(obj, dict):
            # 优先从 Sentence 中取，因为这里的粒度最细
            if "Sentences" in obj and isinstance(obj["Sentences"], list):
                for s in obj["Sentences"]:
                    if isinstance(s, dict):
                        t = s.get("Text")
                        if t: texts.append(t)
                return texts # 如果当前节点找到了句子，就不再深入该节点的其他属性
            
            # 其次找自身的 Text
            t = obj.get("Text")
            if t and isinstance(t, str):
                texts.append(t)
            
            # 递归遍历其他值
            for v in obj.values():
                texts.extend(self._recursive_find_text(v))
                
        elif isinstance(obj, list):
            for item in obj:
                texts.extend(self._recursive_find_text(item))
        return texts

    def _download_json(self, url: str) -> Dict:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def transcribe_audio(self, file_url: str, **kwargs) -> Dict[str, Any]:
        task_id = self.submit_transcription_task(file_url, **kwargs)
        task_data = self.wait_for_completion(task_id)
        parsed_result = self.get_transcription_result(task_data)
        
        return {
            "TaskId": task_id,
            "Status": "SUCCESS",
            "Result": {
                "Text": parsed_result["Text"],
                "Duration": 0,
                "Extra": {
                    "Summary": parsed_result["Summary"],
                    "Chapters": parsed_result["Chapters"],
                    "Questions": parsed_result["Questions"]
                }
            }
        }