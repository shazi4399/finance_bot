"""
Aliyun Tingwu Client Wrapper (Official SDK Version with Config Fix)
修复配置读取路径：从 'tingwu.app_key' 读取 AppKey
"""

import json
import time
import requests
from typing import Any, Dict, Optional, List

# 引入官方 SDK
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tingwu20230930.client import Client as Tingwu2Client
from alibabacloud_tingwu20230930 import models as tingwu_models

from src.utils.logger import get_logger

class TingwuClient:
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger()
        
        # 1. 读取基础鉴权信息 (在 aliyun 节点下)
        self.access_key_id = config.get("aliyun.access_key_id")
        self.access_key_secret = config.get("aliyun.access_key_secret")
        
        # 2. ✅ 修复：读取 AppKey (在 tingwu 节点下，匹配你的 config.yaml)
        # 优先尝试 tingwu.app_key，如果没填则尝试 aliyun.app_key 做兼容
        self.app_key = config.get("tingwu.app_key") or config.get("aliyun.app_key")
        
        # 听悟 V2 主要节点通常在北京
        self.region = "cn-beijing" 
        
        # 3. 校验配置
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError("❌ 阿里云 AccessKey/Secret 未配置 (aliyun.access_key_id)")
        
        if not self.app_key:
            self.logger.error("❌ 严重错误: 未检测到 tingwu.app_key！")
            self.logger.error("请检查 config.yaml 中是否已填写: \n"
                              "tingwu:\n  app_key: '你的AppKey'")
            # 这里不抛出异常，让它在提交时报错，方便看日志
            
        try:
            # 初始化官方客户端
            client_config = open_api_models.Config(
                access_key_id=self.access_key_id,
                access_key_secret=self.access_key_secret
            )
            client_config.endpoint = f"tingwu.{self.region}.aliyuncs.com"
            self.client = Tingwu2Client(client_config)
            self.logger.info(f"✅ 通义听悟 V2.0 客户端初始化成功")

        except Exception as e:
            self.logger.error(f"客户端初始化失败: {e}")
            raise

    def submit_task(self, file_url: str) -> Optional[str]:
        """
        提交任务 (携带 AppKey)
        """
        try:
            # 再次检查 AppKey
            if not self.app_key:
                self.logger.error("❌ 提交终止: AppKey 为空")
                return None

            self.logger.info(f"正在提交任务，AppKey: {self.app_key[:6]}******")

            # 1. 构造任务参数
            # output_level: 0=句子级别(推荐), 1=词级别(过于碎片化)
            transcription_param = tingwu_models.CreateTaskRequestParametersTranscription(
                diarization_enabled=True,  # 区分说话人
                output_level=0,            # 使用句子级别，避免碎片化
            )
            
            # 启用摘要和思维导图
            summarization_param = tingwu_models.CreateTaskRequestParametersSummarization(
                types=["Paragraph", "Conversational", "Questions", "MindMap"]
            )
            
            parameters = tingwu_models.CreateTaskRequestParameters(
                transcription=transcription_param,
                summarization=summarization_param,
                auto_chapters_enabled=True,
                summarization_enabled=True
            )

            # 2. 构造输入
            input_config = tingwu_models.CreateTaskRequestInput(
                file_url=file_url,
                source_language="cn",
                task_key=f"task_{int(time.time())}"
            )

            # 3. 构造完整请求
            request = tingwu_models.CreateTaskRequest(
                type="Offline",
                input=input_config,
                parameters=parameters,
                app_key=self.app_key  # ✅ 传入 AppKey
            )

            # 4. 发送请求
            response = self.client.create_task(request)
            
            if response.body.data and response.body.data.task_id:
                task_id = response.body.data.task_id
                self.logger.info(f"✅ 任务提交成功，TaskID: {task_id}")
                return task_id
            else:
                self.logger.error(f"❌ 任务提交响应异常: {response.body}")
                return None

        except Exception as e:
            self.logger.error(f"❌ 提交任务异常: {e}")
            return None

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        轮询获取结果 (自动处理下载和解析)
        """
        timeout = 900 # 15分钟
        start_time = time.time()
        
        self.logger.info(f"开始轮询任务状态 (ID: {task_id})...")

        while True:
            if time.time() - start_time > timeout:
                self.logger.error("❌ 等待超时")
                return None

            try:
                # 使用 SDK 查询状态
                response = self.client.get_task_info(task_id)
                
                status_data = response.body.data
                task_status = status_data.task_status 
                
                if task_status == "SUCCEEDED" or task_status == "COMPLETED":
                    self.logger.info("✅ 转写任务完成，开始下载结果...")
                    return self._process_success_result(status_data)
                
                elif task_status == "FAILED":
                    self.logger.error(f"❌ 任务失败: {status_data.error_message}")
                    return None
                
                else:
                    time.sleep(5) 

            except Exception as e:
                self.logger.error(f"❌ 轮询异常: {e}")
                time.sleep(3)

    def _process_success_result(self, data: Any) -> Dict[str, Any]:
        """
        处理成功结果：下载 JSON 并解析
        """
        download_url = None
        if hasattr(data, 'result') and data.result:
             if hasattr(data.result, 'transcription_url'):
                 download_url = data.result.transcription_url
             elif hasattr(data.result, 'transcription'):
                 download_url = data.result.transcription
        
        if not download_url:
            self.logger.error("❌ 未找到结果下载链接")
            return None

        try:
            self.logger.info(f"⬇️ 正在下载转写结果 JSON...")
            json_data = self._download_json(download_url)
            
            # 保存调试文件
            with open(f"debug_tingwu_{data.task_id}.json", "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                
            return self._parse_json_content(json_data)

        except Exception as e:
            self.logger.error(f"❌ 结果下载/解析失败: {e}")
            return None

    def _download_json(self, url: str) -> Dict:
        """辅助方法：下载 JSON"""
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _parse_json_content(self, data: Dict) -> Dict[str, Any]:
        """
        增强版解析逻辑：优先使用句子级别，智能合并段落
        """
        transcription = data.get("Transcription", data)

        # 优先尝试提取 Sentences (句子级别，最清晰)
        sentences = transcription.get("Sentences", [])
        if sentences:
            self.logger.info(f"📝 提取到 {len(sentences)} 个句子")
            # 按说话人分组，合并成段落
            segments = self._merge_sentences_by_speaker(sentences)
            return {
                "type": "sentences",
                "segments": segments,
                "full_text": "\n\n".join([s["text"] for s in segments])
            }

        # 其次尝试 Paragraphs (段落级别)
        paragraphs = transcription.get("Paragraphs", [])
        if paragraphs:
            self.logger.info(f"📄 提取到 {len(paragraphs)} 个智能段落")
            segments = []
            for para in paragraphs:
                words = para.get("Words", [])
                if words:
                    # 智能合并词，添加适当的空格和标点
                    para_text = self._smart_merge_words(words)
                    segments.append({
                        "text": para_text,
                        "speaker_id": para.get("SpeakerId", "1"),
                        "start_time": words[0].get("Start", 0) if words else 0,
                        "end_time": words[-1].get("End", 0) if words else 0
                    })

            return {
                "type": "paragraphs",
                "segments": segments,
                "full_text": "\n\n".join([s["text"] for s in segments])
            }

        # 最后尝试递归搜索
        self.logger.warning("⚠️ 标准路径未找到文本，启动递归搜索...")
        all_texts = self._recursive_find_text(data)
        if all_texts:
            self.logger.info(f"🔍 递归提取到 {len(all_texts)} 条文本片段")
            # 合并碎片化的文本
            merged_text = self._merge_fragmented_texts(all_texts)
            return {
                "type": "raw_lines",
                "segments": [{"text": merged_text, "speaker_id": "1", "start_time": 0, "end_time": 0}],
                "full_text": merged_text
            }

        return {"type": "empty", "full_text": "", "segments": []}

    def _merge_sentences_by_speaker(self, sentences: List[Dict]) -> List[Dict]:
        """按说话人合并句子成段落"""
        if not sentences:
            return []

        segments = []
        current_speaker = None
        current_texts = []
        current_start = 0

        for sent in sentences:
            speaker_id = sent.get("SpeakerId", "1")
            text = sent.get("Text", "").strip()

            if not text:
                continue

            # 如果说话人变化，保存当前段落
            if current_speaker and speaker_id != current_speaker:
                if current_texts:
                    segments.append({
                        "text": "".join(current_texts),
                        "speaker_id": current_speaker,
                        "start_time": current_start,
                        "end_time": sent.get("BeginTime", 0)
                    })
                current_texts = []
                current_start = sent.get("BeginTime", 0)

            if not current_speaker:
                current_speaker = speaker_id
                current_start = sent.get("BeginTime", 0)

            current_texts.append(text)

        # 保存最后一个段落
        if current_texts:
            segments.append({
                "text": "".join(current_texts),
                "speaker_id": current_speaker,
                "start_time": current_start,
                "end_time": sentences[-1].get("EndTime", 0) if sentences else 0
            })

        return segments

    def _smart_merge_words(self, words: List[Dict]) -> str:
        """智能合并词，处理标点和空格"""
        if not words:
            return ""

        result = []
        for word in words:
            text = word.get("Text", "")
            if text:
                result.append(text)

        # 直接拼接，中文不需要空格
        merged = "".join(result)

        # 清理多余的空格
        import re
        merged = re.sub(r'\s+', '', merged)  # 移除所有空格
        merged = re.sub(r'([，。！？、；：])\1+', r'\1', merged)  # 去除重复标点

        return merged

    def _merge_fragmented_texts(self, texts: List[str]) -> str:
        """合并碎片化的文本"""
        if not texts:
            return ""

        # 过滤空文本
        texts = [t.strip() for t in texts if t.strip()]

        # 直接拼接
        merged = "".join(texts)

        # 清理
        import re
        merged = re.sub(r'\s+', '', merged)
        merged = re.sub(r'([，。！？、；：])\1+', r'\1', merged)

        return merged

    def _recursive_find_text(self, obj: Any) -> List[str]:
        texts = []
        if isinstance(obj, dict):
            if "Text" in obj and isinstance(obj["Text"], str):
                texts.append(obj["Text"])
            for v in obj.values():
                texts.extend(self._recursive_find_text(v))
        elif isinstance(obj, list):
            for item in obj:
                texts.extend(self._recursive_find_text(item))
        return texts