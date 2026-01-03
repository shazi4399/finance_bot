"""Content analysis and structuring for Feishu documents"""

from typing import Any, Dict

from src.utils.config import Config
from src.utils.logger import get_logger

from .qwen_client import QwenClient


class ContentAnalyzer:
    """Content analyzer for structuring transcript data"""

    def __init__(self, config: Config):
        """
        Initialize content analyzer

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger()

        # Initialize Qwen client
        qwen_config = {
            "api_key": config.get("dashscope.api_key"),
            "model": config.get("dashscope.model", "qwen-max"),
        }

        self.client = QwenClient(qwen_config)

    def analyze_transcript(self, transcript_data: Dict[str, Any], video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transcript and generate structured content for Feishu document

        Args:
            transcript_data: Processed transcript data
            video_info: Video information

        Returns:
            Structured content for Feishu document
        """
        self.logger.info("Analyzing transcript for Feishu document generation")

        try:
            # Extract transcript text
            transcript_text = transcript_data.get("text", "")
            video_title = video_info.get("video_title", video_info.get("title", ""))

            # Analyze content with LLM
            analysis_result = self.client.analyze_content(transcript_text, video_title)

            # Enhance with additional metadata
            enhanced_result = self._enhance_analysis_result(analysis_result, transcript_data, video_info)

            self.logger.info("Content analysis completed successfully")
            return enhanced_result

        except Exception as e:
            self.logger.error(f"Content analysis failed: {e}")
            return self._get_fallback_content(video_info, transcript_data)

    def _enhance_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        transcript_data: Dict[str, Any],
        video_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enhance analysis result with additional metadata"""

        # Add video metadata
        analysis_result["video_metadata"] = {
            "bvid": video_info.get("bvid", ""),
            "title": video_info.get("video_title", video_info.get("title", "")),
            "upload_time": video_info.get("upload_time", ""),
            "duration": transcript_data.get("metadata", {}).get("duration", 0),
            "url": f"https://www.bilibili.com/video/{video_info.get('bvid', '')}",
        }

        # Add transcript metadata
        analysis_result["transcript_metadata"] = {
            "word_count": transcript_data.get("metadata", {}).get("word_count", 0),
            "speaker_count": len(transcript_data.get("speakers", {})),
            "chapter_count": len(transcript_data.get("chapters", [])),
            "language": transcript_data.get("metadata", {}).get("language", "zh-CN"),
        }

        # Add speaker information
        analysis_result["speakers"] = transcript_data.get("speakers", {})

        # Add chapters if available
        if transcript_data.get("chapters"):
            analysis_result["chapters"] = transcript_data["chapters"]

        # Add processing timestamp
        from datetime import datetime

        analysis_result["processed_at"] = datetime.now().isoformat()

        return analysis_result

    def _get_fallback_content(self, video_info: Dict[str, Any], transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback content when analysis fails"""
        video_title = video_info.get("video_title", video_info.get("title", "未知视频"))
        transcript_text = transcript_data.get("text", "")

        return {
            "title": video_title,
            "summary": transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text,
            "tags": ["视频", "转录"],
            "key_insights": [
                {
                    "heading": "转录内容",
                    "content": "内容分析暂时不可用，请查看原始转录文本。",
                }
            ],
            "data_table": {"headers": [], "rows": []},
            "action_items": [],
            "topics": ["视频内容"],
            "sentiment": "neutral",
            "category": "general",
            "video_metadata": {
                "bvid": video_info.get("bvid", ""),
                "title": video_title,
                "upload_time": video_info.get("upload_time", ""),
                "url": f"https://www.bilibili.com/video/{video_info.get('bvid', '')}",
            },
            "transcript_metadata": {
                "word_count": len(transcript_text),
                "speaker_count": len(transcript_data.get("speakers", {})),
                "chapter_count": len(transcript_data.get("chapters", [])),
                "language": "zh-CN",
            },
            "speakers": transcript_data.get("speakers", {}),
            "error": "Content analysis failed",
        }

    def structure_for_feishu_blocks(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure analysis result for Feishu Block architecture

        Args:
            analysis_result: Analysis result from LLM

        Returns:
            Structured data for Feishu document blocks
        """
        self.logger.info("Structuring content for Feishu blocks")

        try:
            # Build block structure
            blocks = []

            # 1. Title block (Heading 1)
            title = analysis_result.get("title", "视频内容分析")
            blocks.append({"type": "heading_1", "content": title})

            # 2. Video metadata callout
            video_metadata = analysis_result.get("video_metadata", {})
            if video_metadata.get("bvid"):
                metadata_text = "📹 **视频信息**\n"
                metadata_text += f"• BVID: {video_metadata.get('bvid', '')}\n"
                metadata_text += f"• 上传时间: {video_metadata.get('upload_time', '')}\n"
                metadata_text += f"• 视频链接: {video_metadata.get('url', '')}"

                blocks.append({"type": "callout", "style": "blue", "content": metadata_text})

            # 3. Summary callout
            summary = analysis_result.get("summary", "")
            if summary:
                blocks.append(
                    {
                        "type": "callout",
                        "style": "green",
                        "content": f"📝 **内容摘要**\n{summary}",
                    }
                )

            # 4. Positions Table (High-Fidelity Extraction)
            positions = analysis_result.get("positions", [])
            if positions:
                blocks.append({"type": "heading_2", "content": "📊 持仓变动与逻辑"})

                headers = ["标的", "操作", "详情", "逻辑"]
                rows = []
                for pos in positions:
                    rows.append(
                        [
                            pos.get("name", "-"),
                            pos.get("action", "-"),
                            pos.get("position_details", "-"),
                            pos.get("logic", "-"),
                        ]
                    )

                blocks.append({"type": "table", "headers": headers, "rows": rows})

            # 5. Quotes (Gold Sentences)
            quotes = analysis_result.get("quotes", [])
            if quotes:
                blocks.append({"type": "heading_2", "content": "💬 核心金句"})

                for quote in quotes:
                    blocks.append({"type": "callout", "style": "yellow", "content": f"“{quote}”"})

            # 6. Verbatim Transcript (Full Text)
            formatted_full_text = analysis_result.get("formatted_full_text", "")
            if formatted_full_text:
                blocks.append({"type": "heading_2", "content": "📝 全文逐字稿 (精修版)"})

                # Feishu text blocks might have limits, but we'll try sending as one text block first.
                # Ideally, we should split if too long, but let's assume it fits or Feishu handles it.
                # Using 'text' type which maps to paragraph/text run.
                blocks.append({"type": "text", "content": formatted_full_text})

            # 7. Footer
            from datetime import datetime

            processed_at = analysis_result.get("processed_at", datetime.now().isoformat())
            blocks.append({"type": "divider"})

            blocks.append(
                {
                    "type": "text",
                    "content": f"📅 生成时间: {processed_at[:10]} {processed_at[11:19]}\n🤖 由内容情报流水线自动生成",
                }
            )

            return {"title": title, "blocks": blocks}

        except Exception as e:
            self.logger.error(f"Failed to structure content for Feishu: {e}")
            return self._get_fallback_blocks(analysis_result)

    def _get_fallback_blocks(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback block structure when structuring fails"""
        title = analysis_result.get("title", "视频内容分析")

        fallback_blocks = [
            {"type": "heading_1", "content": title},
            {
                "type": "callout",
                "style": "red",
                "content": "⚠️ 文档结构化失败，请检查原始数据。",
            },
        ]

        return {"title": title, "blocks": fallback_blocks}
