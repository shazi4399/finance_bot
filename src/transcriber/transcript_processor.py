"""Transcription result processing and cleaning"""

import re
from typing import Any, Dict, List

from src.utils.logger import get_logger


class TranscriptProcessor:
    """Process and clean transcription results"""

    def __init__(self):
        """Initialize transcript processor"""
        self.logger = get_logger()

    def process_transcript(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw transcription result into structured format

        Args:
            raw_result: Raw transcription result from Tingwu

        Returns:
            Processed transcript dictionary
        """
        self.logger.info("Processing transcription result")

        try:
            processed = {
                "text": self._extract_full_text(raw_result),
                "segments": self._extract_segments(raw_result),
                "speakers": self._extract_speaker_info(raw_result),
                "chapters": self._extract_chapters(raw_result),
                "summary": self._extract_summary(raw_result),
                "metadata": self._extract_metadata(raw_result),
            }

            self.logger.info(f"Processed transcript: {len(processed['segments'])} segments")
            return processed

        except Exception as e:
            self.logger.error(f"Failed to process transcript: {e}")
            return {
                "text": "",
                "segments": [],
                "speakers": {},
                "chapters": [],
                "summary": "",
                "metadata": {},
                "error": str(e),
            }

    def _extract_full_text(self, raw_result: Dict[str, Any]) -> str:
        """Extract full text from transcription result"""
        try:
            # Try different possible result structures
            if "Result" in raw_result:
                result = raw_result["Result"]
            elif "Transcript" in raw_result:
                result = raw_result["Transcript"]
            else:
                result = raw_result

            # Extract sentences or paragraphs
            text_parts = []

            if "Sentences" in result:
                for sentence in result["Sentences"]:
                    text = sentence.get("Text", "").strip()
                    if text:
                        text_parts.append(text)

            elif "Paragraphs" in result:
                for paragraph in result["Paragraphs"]:
                    text = paragraph.get("Text", "").strip()
                    if text:
                        text_parts.append(text)

            elif "Text" in result:
                text_parts.append(result["Text"].strip())

            full_text = " ".join(text_parts)

            # Clean up extra spaces and normalize
            full_text = re.sub(r"\s+", " ", full_text).strip()

            return full_text

        except Exception as e:
            self.logger.error(f"Failed to extract full text: {e}")
            return ""

    def _extract_segments(self, raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract time-coded segments from transcription result"""
        try:
            # Try different possible result structures
            if "Result" in raw_result:
                result = raw_result["Result"]
            elif "Transcript" in raw_result:
                result = raw_result["Transcript"]
            else:
                result = raw_result

            segments = []

            if "Sentences" in result:
                for sentence in result["Sentences"]:
                    segment = {
                        "text": sentence.get("Text", "").strip(),
                        "start_time": sentence.get("BeginTime", 0),
                        "end_time": sentence.get("EndTime", 0),
                        "speaker_id": sentence.get("SpeakerId", 0),
                        "confidence": sentence.get("Confidence", 0.0),
                    }

                    if segment["text"]:
                        segments.append(segment)

            elif "Words" in result:
                # Process word-level segments
                current_segment = {
                    "text": "",
                    "start_time": 0,
                    "end_time": 0,
                    "speaker_id": 0,
                    "confidence": 0.0,
                }

                for word in result["Words"]:
                    word_text = word.get("Word", "").strip()
                    if not word_text:
                        continue

                    # Start new segment if speaker changes
                    speaker_id = word.get("SpeakerId", 0)
                    if speaker_id != current_segment["speaker_id"] and current_segment["text"]:
                        segments.append(current_segment.copy())
                        current_segment["text"] = ""
                        current_segment["start_time"] = word.get("BeginTime", 0)

                    current_segment["text"] += word_text + " "
                    current_segment["end_time"] = word.get("EndTime", 0)
                    current_segment["speaker_id"] = speaker_id
                    current_segment["confidence"] = max(current_segment["confidence"], word.get("Confidence", 0.0))

                # Add last segment
                if current_segment["text"]:
                    current_segment["text"] = current_segment["text"].strip()
                    segments.append(current_segment)

            # Sort by start time
            segments.sort(key=lambda x: x["start_time"])

            return segments

        except Exception as e:
            self.logger.error(f"Failed to extract segments: {e}")
            return []

    def _extract_speaker_info(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract speaker information from transcription result"""
        try:
            # Try different possible result structures
            if "Result" in raw_result:
                result = raw_result["Result"]
            elif "Transcript" in raw_result:
                result = raw_result["Transcript"]
            else:
                result = raw_result

            speakers = {}

            if "SpeakerLabels" in result:
                for speaker in result["SpeakerLabels"]:
                    speaker_id = str(speaker.get("SpeakerId", ""))
                    speaker_name = speaker.get("SpeakerName", f"Speaker {speaker_id}")

                    speakers[speaker_id] = {
                        "id": speaker_id,
                        "name": speaker_name,
                        "gender": speaker.get("Gender", "unknown"),
                        "confidence": speaker.get("Confidence", 0.0),
                    }

            elif "Speakers" in result:
                for speaker in result["Speakers"]:
                    speaker_id = str(speaker.get("Id", ""))
                    speaker_name = speaker.get("Name", f"Speaker {speaker_id}")

                    speakers[speaker_id] = {
                        "id": speaker_id,
                        "name": speaker_name,
                        "gender": speaker.get("Gender", "unknown"),
                        "confidence": speaker.get("Confidence", 0.0),
                    }

            return speakers

        except Exception as e:
            self.logger.error(f"Failed to extract speaker info: {e}")
            return {}

    def _extract_chapters(self, raw_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract chapter information from transcription result"""
        try:
            # Try different possible result structures
            if "Result" in raw_result:
                result = raw_result["Result"]
            elif "Transcript" in raw_result:
                result = raw_result["Transcript"]
            else:
                result = raw_result

            chapters = []

            if "Chapters" in result:
                for chapter in result["Chapters"]:
                    chapter_info = {
                        "title": chapter.get("Title", "").strip(),
                        "summary": chapter.get("Summary", "").strip(),
                        "start_time": chapter.get("StartTime", 0),
                        "end_time": chapter.get("EndTime", 0),
                        "confidence": chapter.get("Confidence", 0.0),
                    }

                    if chapter_info["title"]:
                        chapters.append(chapter_info)

            return chapters

        except Exception as e:
            self.logger.error(f"Failed to extract chapters: {e}")
            return []

    def _extract_summary(self, raw_result: Dict[str, Any]) -> str:
        """Extract summary from transcription result"""
        try:
            # Try different possible result structures
            if "Result" in raw_result:
                result = raw_result["Result"]
            elif "Transcript" in raw_result:
                result = raw_result["Transcript"]
            else:
                result = raw_result

            summary = ""

            if "Summary" in result:
                summary = result["Summary"].strip()
            elif "Abstract" in result:
                summary = result["Abstract"].strip()

            return summary

        except Exception as e:
            self.logger.error(f"Failed to extract summary: {e}")
            return ""

    def _extract_metadata(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from transcription result"""
        try:
            metadata = {
                "task_id": raw_result.get("TaskId", ""),
                "status": raw_result.get("Status", ""),
                "duration": 0,
                "word_count": 0,
                "language": "zh-CN",
            }

            # Try different possible result structures
            if "Result" in raw_result:
                result = raw_result["Result"]
            elif "Transcript" in raw_result:
                result = raw_result["Transcript"]
            else:
                result = raw_result

            # Extract duration
            if "Duration" in result:
                metadata["duration"] = result["Duration"]
            elif "AudioDuration" in result:
                metadata["duration"] = result["AudioDuration"]

            # Extract word count
            if "WordCount" in result:
                metadata["word_count"] = result["WordCount"]

            # Extract language
            if "Language" in result:
                metadata["language"] = result["Language"]

            return metadata

        except Exception as e:
            self.logger.error(f"Failed to extract metadata: {e}")
            return {}

    def format_for_llm(self, processed_transcript: Dict[str, Any]) -> str:
        """
        Format processed transcript for LLM consumption

        Args:
            processed_transcript: Processed transcript dictionary

        Returns:
            Formatted text string
        """
        try:
            formatted_parts = []

            # Add summary if available
            if processed_transcript.get("summary"):
                formatted_parts.append(f"摘要：{processed_transcript['summary']}")
                formatted_parts.append("")

            # Add chapters if available
            chapters = processed_transcript.get("chapters", [])
            if chapters:
                formatted_parts.append("章节：")
                for i, chapter in enumerate(chapters, 1):
                    formatted_parts.append(f"{i}. {chapter['title']}")
                    if chapter.get("summary"):
                        formatted_parts.append(f"   {chapter['summary']}")
                formatted_parts.append("")

            # Add main content with speaker labels
            segments = processed_transcript.get("segments", [])
            speakers = processed_transcript.get("speakers", {})

            if segments:
                formatted_parts.append("转录内容：")

                current_speaker = None
                for segment in segments:
                    speaker_id = str(segment.get("speaker_id", 0))
                    speaker_name = speakers.get(speaker_id, {}).get("name", f"Speaker {speaker_id}")

                    # Add speaker label if changed
                    if speaker_id != current_speaker:
                        formatted_parts.append(f"\n{speaker_name}：")
                        current_speaker = speaker_id

                    # Add segment text
                    formatted_parts.append(segment["text"])

            return "\n".join(formatted_parts)

        except Exception as e:
            self.logger.error(f"Failed to format transcript for LLM: {e}")
            return processed_transcript.get("text", "")

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove filler words and patterns
        filler_patterns = [
            r"\b[嗯啊呃哦唉]\b",
            r"\b[那个这个]\b",
            r"\b[就是说就是]\b",
            r"\b[然后那么]\b",
        ]

        for pattern in filler_patterns:
            text = re.sub(pattern, "", text)

        # Clean up punctuation
        text = re.sub(r"[，。！？；：]", "，", text)
        text = re.sub(r"[,，]{2,}", "，", text)

        # Strip and return
        return text.strip()
