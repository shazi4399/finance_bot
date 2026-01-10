"""Content analysis and structuring for Feishu documents"""

from typing import Any, Dict, List

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

        # Add segments for raw transcript display
        analysis_result["segments"] = transcript_data.get("segments", [])

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
                blocks.append({
                    "type": "callout",
                    "style": "grey",
                    "content": "以下是经过LLM智能整理的全文逐字稿，保留了原话的真实性，同时优化了段落结构。"
                })

                # Split into paragraphs for better readability
                paragraphs = formatted_full_text.split("\n\n")
                for paragraph in paragraphs:
                    if paragraph.strip():
                        # Add each paragraph as a separate text block
                        blocks.append({"type": "text", "content": paragraph.strip()})
                        # Add a small spacer between paragraphs
                        blocks.append({"type": "text", "content": ""})

            # 7. Optional: Raw Transcript with Timestamps (if available)
            transcript_metadata = analysis_result.get("transcript_metadata", {})
            segments = analysis_result.get("segments", [])

            # Only show timestamped transcript if we have meaningful segments
            if segments and len(segments) > 0:
                raw_transcript = self._format_raw_transcript(analysis_result)
                if raw_transcript:
                    blocks.append({"type": "heading_2", "content": "⏱️ 原始转录（含时间戳）"})
                    blocks.append(
                        {
                            "type": "callout",
                            "style": "grey",
                            "content": "💡 提示：时间戳格式为 [MM:SS] 或 [HH:MM:SS]，方便您快速定位到视频的具体位置。",
                        }
                    )
                    # Split into chunks to avoid too long blocks (max 30 lines per block)
                    for chunk in self._split_transcript_into_chunks(raw_transcript, max_lines=30):
                        blocks.append({"type": "text", "content": chunk})

            # 8. Footer
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

    def _format_raw_transcript(self, analysis_result: Dict[str, Any]) -> str:
        """
        Format raw transcript with timestamps and speaker labels

        Args:
            analysis_result: Analysis result containing transcript data

        Returns:
            Formatted transcript string with timestamps
        """
        try:
            # Try to get segments from various sources
            segments = []

            # Check if we have raw transcript data
            if "segments" in analysis_result:
                segments = analysis_result["segments"]
            elif "transcript_data" in analysis_result:
                transcript_data = analysis_result["transcript_data"]
                segments = transcript_data.get("segments", [])

            if not segments:
                return ""

            # Get speaker information
            speakers = analysis_result.get("speakers", {})

            # Format segments with timestamps
            formatted_lines = []
            current_speaker = None

            for segment in segments:
                speaker_id = str(segment.get("speaker_id", 0))
                speaker_name = speakers.get(speaker_id, {}).get("name", f"说话人{speaker_id}")
                text = segment.get("text", "").strip()

                if not text:
                    continue

                # Format timestamp
                start_time = segment.get("start_time", 0)
                timestamp = self._format_timestamp(start_time)

                # Add speaker label if changed
                if speaker_id != current_speaker:
                    if formatted_lines:  # Add blank line between speakers
                        formatted_lines.append("")
                    formatted_lines.append(f"【{speaker_name}】")
                    current_speaker = speaker_id

                # Add timestamped text
                formatted_lines.append(f"[{timestamp}] {text}")

            return "\n".join(formatted_lines)

        except Exception as e:
            self.logger.error(f"Failed to format raw transcript: {e}")
            return ""

    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in MM:SS or HH:MM:SS format

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        try:
            seconds = int(seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60

            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                return f"{minutes:02d}:{secs:02d}"

        except Exception:
            return "00:00"

    def _split_transcript_into_chunks(self, transcript: str, max_lines: int = 50) -> List[str]:
        """
        Split transcript into chunks of maximum lines

        Args:
            transcript: Full transcript text
            max_lines: Maximum lines per chunk

        Returns:
            List of transcript chunks
        """
        if not transcript:
            return []

        lines = transcript.split("\n")
        chunks = []

        for i in range(0, len(lines), max_lines):
            chunk_lines = lines[i : i + max_lines]
            chunks.append("\n".join(chunk_lines))

        return chunks
