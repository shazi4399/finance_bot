"""Main LLM processor module combining Qwen client and content analysis"""

from typing import Any, Dict, Optional

from src.utils.config import Config
from src.utils.logger import get_logger

from .content_analyzer import ContentAnalyzer
from .qwen_client import QwenClient


class LLMProcessor:
    """Main LLM processor class"""

    def __init__(self, config: Config):
        """
        Initialize LLM processor

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize components
        self.analyzer = ContentAnalyzer(config)

        # Initialize Qwen client for direct access
        qwen_config = {
            "api_key": config.get("dashscope.api_key"),
            "model": config.get("dashscope.model", "qwen-max"),
        }
        self.client = QwenClient(qwen_config)

    def process_transcript(
        self, transcript_data: Dict[str, Any], video_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process transcript and generate structured content

        Args:
            transcript_data: Processed transcript data
            video_info: Video information

        Returns:
            Structured content for Feishu document or None if failed
        """
        self.logger.info("Processing transcript with LLM")

        try:
            # Analyze transcript
            analysis_result = self.analyzer.analyze_transcript(transcript_data, video_info)

            # Structure for Feishu blocks
            feishu_content = self.analyzer.structure_for_feishu_blocks(analysis_result)

            self.logger.info("LLM processing completed successfully")
            return feishu_content

        except Exception as e:
            self.logger.error(f"LLM processing failed: {e}")
            return None

    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate summary of text

        Args:
            text: Text to summarize
            max_length: Maximum summary length

        Returns:
            Generated summary
        """
        return self.client.generate_summary(text, max_length)

    def extract_keywords(self, text: str, max_keywords: int = 10) -> list:
        """
        Extract keywords from text

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords

        Returns:
            List of keywords
        """
        return self.client.extract_keywords(text, max_keywords)

    def analyze_sentiment(self, text: str) -> str:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze

        Returns:
            Sentiment label (positive/neutral/negative)
        """
        prompt = f"""
请分析以下文本的情感倾向，只输出以下三个选项之一：positive（积极）、neutral（中性）、negative（消极）

文本：
{text}
"""

        try:
            result = self.client.generate_text(prompt, temperature=0.1, max_tokens=10)
            result = result.strip().lower()

            # Validate result
            if result in ["positive", "neutral", "negative"]:
                return result
            else:
                return "neutral"

        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            return "neutral"

    def categorize_content(self, text: str) -> str:
        """
        Categorize content

        Args:
            text: Text to categorize

        Returns:
            Content category
        """
        prompt = f"""
请将以下内容分类到以下类别之一：技术、商业、教育、娱乐、生活、新闻、其他

文本：
{text}

只输出类别名称：
"""

        try:
            result = self.client.generate_text(prompt, temperature=0.1, max_tokens=10)
            result = result.strip()

            # Validate result
            valid_categories = ["技术", "商业", "教育", "娱乐", "生活", "新闻", "其他"]
            if result in valid_categories:
                return result
            else:
                return "其他"

        except Exception as e:
            self.logger.error(f"Content categorization failed: {e}")
            return "其他"

    def extract_key_points(self, text: str, max_points: int = 5) -> list:
        """
        Extract key points from text

        Args:
            text: Text to extract key points from
            max_points: Maximum number of key points

        Returns:
            List of key points
        """
        prompt = f"""
请从以下文本中提取{max_points}个关键要点，以JSON数组格式输出：

文本：
{text}

输出格式：["要点1", "要点2", ...]
"""

        try:
            result = self.client.generate_json(prompt)
            if isinstance(result, list):
                return result[:max_points]
            else:
                return []

        except Exception as e:
            self.logger.error(f"Key points extraction failed: {e}")
            return []

    def generate_action_items(self, text: str, max_items: int = 5) -> list:
        """
        Generate action items from text

        Args:
            text: Text to generate action items from
            max_items: Maximum number of action items

        Returns:
            List of action items
        """
        prompt = f"""
请从以下文本中生成{max_items}个可执行的行动事项，以JSON数组格式输出：

文本：
{text}

输出格式：["行动事项1", "行动事项2", ...]
"""

        try:
            result = self.client.generate_json(prompt)
            if isinstance(result, list):
                return result[:max_items]
            else:
                return []

        except Exception as e:
            self.logger.error(f"Action items generation failed: {e}")
            return []
