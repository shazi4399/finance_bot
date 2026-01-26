"""Tongyi Qianwen LLM client implementation"""

import json
import re
from typing import Any, Dict, List, Optional

import dashscope
from dashscope import Generation

from src.utils.logger import get_logger
from src.utils.retry import APIError, NetworkError, with_retry


class QwenClient:
    """Tongyi Qianwen LLM client"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Qwen client

        Args:
            config: Qwen configuration dictionary
        """
        self.config = config
        self.logger = get_logger()

        # Extract configuration
        self.api_key = config.get("api_key")
        self.model = config.get("model", "qwen-max")

        # Validate configuration
        if not self.api_key:
            raise ValueError("Qwen API key not configured")

        # Initialize DashScope
        dashscope.api_key = self.api_key

        self.logger.info(f"Qwen client initialized with model: {self.model}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Qwen model

        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        self.logger.debug(f"Generating text with model: {self.model}")

        # Default parameters
        params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "result_format": "message",
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "top_p": kwargs.get("top_p", 0.8),
        }

        try:
            response = Generation.call(**params)

            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                error_msg = f"API error: {response.message}"
                self.logger.error(error_msg)
                raise APIError(error_msg)

        except Exception as e:
            self.logger.error(f"Failed to generate text: {e}")
            raise APIError(f"Text generation failed: {e}")

    @with_retry(max_attempts=3, exceptions=(NetworkError, APIError))
    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON output using Qwen model

        Args:
            prompt: Input prompt
            schema: Optional JSON schema for output validation
            **kwargs: Additional generation parameters

        Returns:
            Generated JSON dictionary
        """
        self.logger.debug(f"Generating JSON with model: {self.model}")

        # Build system prompt for JSON generation
        system_prompt = "你是一个专业的数据分析师。请严格按照JSON格式输出结果，不要包含任何Markdown标记或解释文字。"

        if schema:
            system_prompt += f"\n\n请按照以下JSON Schema格式输出：\n{json.dumps(schema, ensure_ascii=False, indent=2)}"

        # Default parameters for JSON generation
        params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "result_format": "message",
            "temperature": kwargs.get("temperature", 0.3),  # Lower temperature for structured output
            "max_tokens": kwargs.get("max_tokens", 3000),
            "top_p": kwargs.get("top_p", 0.8),
        }

        try:
            response = Generation.call(**params)

            if response.status_code == 200:
                content = response.output.choices[0].message.content

                # Clean and parse JSON
                return self._clean_and_parse_json(content)
            else:
                error_msg = f"API error: {response.message}"
                self.logger.error(error_msg)
                raise APIError(error_msg)

        except Exception as e:
            self.logger.error(f"Failed to generate JSON: {e}")
            raise APIError(f"JSON generation failed: {e}")

    def _clean_and_parse_json(self, content: str) -> Dict[str, Any]:
        """
        Clean content and parse as JSON

        Args:
            content: Raw content from LLM

        Returns:
            Parsed JSON dictionary
        """
        content = re.sub(r"```json\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()

        def _truncate(s: str, head: int = 800, tail: int = 800) -> str:
            if len(s) <= head + tail:
                return s
            return f"{s[:head]}\n...\n{s[-tail:]}"

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            self.logger.debug(f"Content that failed to parse (truncated): {_truncate(content)}")

        extracted = self._extract_json_substring(content)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse extracted JSON: {e}")

            try:
                extracted_fixed = re.sub(r",\s*}", "}", extracted)
                extracted_fixed = re.sub(r",\s*]", "]", extracted_fixed)
                extracted_fixed = re.sub(r"[\x00-\x08\x0B-\x1F]", "", extracted_fixed)
                return json.loads(extracted_fixed)
            except json.JSONDecodeError:
                pass

        try:
            content_fixed = re.sub(r",\s*}", "}", content)
            content_fixed = re.sub(r",\s*]", "]", content_fixed)
            content_fixed = re.sub(r"[\x00-\x08\x0B-\x1F]", "", content_fixed)
            return json.loads(content_fixed)
        except json.JSONDecodeError as e:
            return {
                "error": "Failed to parse JSON",
                "raw_content_truncated": _truncate(content),
                "parse_error": str(e),
            }

    def _extract_json_substring(self, content: str) -> Optional[str]:
        start_candidates = []
        for i, ch in enumerate(content):
            if ch == "{" or ch == "[":
                start_candidates.append(i)
                break

        if not start_candidates:
            return None

        start = start_candidates[0]
        opening = content[start]
        closing = "}" if opening == "{" else "]"

        stack = []
        in_string = False
        escape = False

        for idx in range(start, len(content)):
            ch = content[idx]

            if in_string:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == "\"":
                    in_string = False
                continue

            if ch == "\"":
                in_string = True
                continue

            if ch == "{" or ch == "[":
                stack.append(ch)
                continue
            if ch == "}" or ch == "]":
                if not stack:
                    continue
                last = stack.pop()
                if (last == "{" and ch != "}") or (last == "[" and ch != "]"):
                    return None
                if not stack and ch == closing:
                    return content[start : idx + 1].strip()

        return None

    def analyze_content(self, transcript_text: str, video_title: str = "") -> Dict[str, Any]:
        """
        Analyze transcript content and extract structured information

        Args:
            transcript_text: Transcript text to analyze
            video_title: Original video title

        Returns:
            Structured analysis result
        """
        self.logger.info("Analyzing content with Qwen LLM")

        max_full_text_chars = int(self.config.get("max_full_text_chars", 3000))
        is_long_transcript = len(transcript_text) > max_full_text_chars

        compact_prompt = f"""
你是一位专业的财经复盘记录员，擅长处理语音转录文本。请对转录内容进行“高保真逻辑提取”，并生成简洁摘要。

要求：
1. 保留原话，不要改写关键表达。
2. 数据优先，必须精确提取所有提到的数字（仓位金额、百分比、股价）。
3. 拒绝脑补，博主没说的不要总结。
4. 只输出一个 JSON 对象，不要输出任何解释文字。

注意：本次转录内容较长，请不要在 JSON 中输出完整逐字稿，只需输出摘要、持仓变动、金句。

视频标题：{video_title}

转录内容：
{transcript_text}

输出 JSON 字段：
{{
  "title": "生成一个吸引人的标题，格式：日期 | 核心金句",
  "summary": "200字以内的今日核心概览（包含当日盈亏、市场定性）",
  "positions": [{{"name":"","action":"","position_details":"","logic":""}}],
  "quotes": ["金句1","金句2"]
}}
"""
        compact_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "positions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "action": {"type": "string"},
                            "position_details": {"type": "string"},
                            "logic": {"type": "string"},
                        },
                        "required": ["name", "action", "position_details", "logic"],
                    },
                },
                "quotes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "summary", "positions", "quotes"],
        }

        full_prompt = f"""
你是一位专业的财经复盘记录员，擅长处理语音转录文本。你的任务是将杂乱的语音转录文本处理成两部分内容。

### 任务一：全文逐字稿精修 (Verbatim Transcript)
* **目标**：将输入的语音转录文本整理成易于阅读的文章格式。
* **要求**：
    1.  **智能分段**：根据语义和话题转换，将长文本切分成合理的段落。
    2.  **标点修正**：修复转录中缺失或错误的标点符号。
    3.  **绝对忠实**：**严禁**删减任何内容，**严禁**改写措辞。必须保留博主的口癖（如“这个这个”、“对吧”）、方言词汇和情绪表达。

### 任务二：高保真逻辑提取 (High-Fidelity Extraction)
* **目标**：提取博主的交易逻辑和持仓变动，保持“原汁原味”。
* **原则**：
    1.  **保留原话**：不要把“爹妈养娃”改成“股东回报机制”，直接用原话，或者括号备注。
    2.  **数据优先**：必须精确提取所有提到的数字（仓位金额、百分比、股价）。
    3.  **拒绝脑补**：博主没说的不要强行总结。

视频标题：{video_title}

转录内容：
{transcript_text}

### 输出格式 (JSON)
请返回严格的 JSON 格式，包含以下字段：
{{
    "title": "生成一个吸引人的标题，格式：日期 | 核心金句",
    "summary": "200字以内的今日核心概览（包含当日盈亏、市场定性）",
    "formatted_full_text": "这里放入处理好的全文逐字稿，保留换行符",
    "positions": [
        {{
            "name": "标的名称（如神威药业）",
            "action": "加仓/减仓/锁仓/做T",
            "position_details": "具体的仓位描述（如'进场20万'、'剩47.8万'）",
            "logic": "博主的原话逻辑（保留通俗比喻，列出1.2.3点）"
        }}
    ],
    "quotes": [
        "提取博主原话金句1",
        "提取博主原话金句2"
    ]
}}
"""
        full_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "formatted_full_text": {"type": "string"},
                "positions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "action": {"type": "string"},
                            "position_details": {"type": "string"},
                            "logic": {"type": "string"},
                        },
                        "required": ["name", "action", "position_details", "logic"],
                    },
                },
                "quotes": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "title",
                "summary",
                "formatted_full_text",
                "positions",
                "quotes",
            ],
        }

        try:
            if is_long_transcript:
                result = self.generate_json(compact_prompt, schema=compact_schema)
                if "error" in result:
                    self.logger.error(f"LLM analysis failed: {result['error']}")
                    return self._get_fallback_result(video_title, transcript_text)

                result.setdefault("formatted_full_text", "")
                result = self._ensure_required_fields(result, video_title, transcript_text)
                self.logger.info("Content analysis completed successfully")
                return result

            result = self.generate_json(full_prompt, schema=full_schema)
            if "error" not in result:
                result = self._ensure_required_fields(result, video_title, transcript_text)
                self.logger.info("Content analysis completed successfully")
                return result

            self.logger.error(f"LLM analysis failed: {result['error']}")
            result = self.generate_json(compact_prompt, schema=compact_schema)
            if "error" in result:
                self.logger.error(f"LLM analysis failed: {result['error']}")
                return self._get_fallback_result(video_title, transcript_text)

            result.setdefault("formatted_full_text", "")
            result = self._ensure_required_fields(result, video_title, transcript_text)
            self.logger.info("Content analysis completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Content analysis failed: {e}")
            return self._get_fallback_result(video_title, transcript_text)

    def _ensure_required_fields(self, result: Dict[str, Any], video_title: str, transcript_text: str) -> Dict[str, Any]:
        """Ensure all required fields exist in the result"""
        # Set default title if missing
        if not result.get("title"):
            result["title"] = video_title or "视频内容分析"

        # Set default summary if missing
        if not result.get("summary"):
            # Generate simple summary from first 200 characters
            summary = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
            result["summary"] = summary

        # Ensure new fields exist
        result.setdefault("formatted_full_text", transcript_text)
        result.setdefault("positions", [])
        result.setdefault("quotes", [])

        return result

    def _get_fallback_result(self, video_title: str, transcript_text: str) -> Dict[str, Any]:
        """Get fallback result when LLM analysis fails"""
        return {
            "title": video_title or "视频内容分析",
            "summary": transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text,
            "tags": ["视频", "内容"],
            "key_insights": [
                {
                    "heading": "主要内容",
                    "content": "视频内容分析暂时不可用，请查看原始转录文本。",
                }
            ],
            "data_table": {"headers": [], "rows": []},
            "action_items": [],
            "topics": ["视频内容"],
            "sentiment": "neutral",
            "category": "general",
            "error": "LLM analysis failed",
        }

    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate summary of text

        Args:
            text: Text to summarize
            max_length: Maximum summary length

        Returns:
            Generated summary
        """
        prompt = f"""
请为以下文本生成一个简洁的摘要，不超过{max_length}字：

{text}
"""

        try:
            summary = self.generate_text(prompt, temperature=0.3, max_tokens=500)
            return summary.strip()

        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            # Return truncated text as fallback
            return text[:max_length] + "..." if len(text) > max_length else text

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords

        Returns:
            List of keywords
        """
        prompt = f"""
请从以下文本中提取{max_keywords}个最重要的关键词，以JSON数组格式输出：

{text}

输出格式：["关键词1", "关键词2", ...]
"""

        try:
            result = self.generate_json(prompt)
            if isinstance(result, list):
                return result[:max_keywords]
            elif isinstance(result, dict) and "keywords" in result:
                return result["keywords"][:max_keywords]
            else:
                return []

        except Exception as e:
            self.logger.error(f"Failed to extract keywords: {e}")
            return []
