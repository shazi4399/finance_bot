"""
Feishu Block Builder - 将结构化数据转换为飞书 DocX Block 结构
使用飞书 DocX API 原生块类型 (Heading, Bullet, etc.) 以获得更好的排版效果
"""
from typing import List, Dict, Any, Optional

class BlockBuilder:
    def build_blocks(self, content_data: Dict[str, Any], video_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        构建完整的文档内容块
        
        Args:
            content_data: LLM 分析后的内容数据
            video_info: 视频元数据 (标题, URL, 时长等)
        """
        blocks = []

        # 1. 头部信息 (标题 + 元数据)
        if video_info:
            # H1 标题
            title = video_info.get("title", content_data.get("title", "未命名复盘"))
            blocks.append(self._create_heading_block(title, level=1))
            
            blocks.append(self._create_heading_block("📌 视频信息", level=3))

            if "bvid" in video_info and video_info["bvid"]:
                blocks.append(self._create_bullet_block(f"🎬 BVID: {video_info['bvid']}"))

            if "upload_time" in video_info and video_info["upload_time"]:
                blocks.append(self._create_bullet_block(f"📅 发布时间: {video_info['upload_time']}"))

            if "duration" in video_info and video_info["duration"]:
                duration = video_info["duration"]
                duration_str = str(duration)
                if isinstance(duration, int):
                    m, s = divmod(duration, 60)
                    h, m = divmod(m, 60)
                    duration_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                blocks.append(self._create_bullet_block(f"⏱️ 视频时长: {duration_str}"))

            if "url" in video_info and video_info["url"]:
                blocks.append(self._create_bullet_block(f"🔗 视频链接: {video_info['url']}"))
            
            blocks.append(self._create_text_block(""))  # 空行分隔

        # 2. 内容主体
        # 检查是否已经是结构化的 blocks 格式
        if "blocks" in content_data:
            # 新格式：直接使用 content_analyzer 生成的 blocks
            blocks.extend(self._convert_blocks_to_feishu_format(content_data["blocks"]))
            return blocks

        # 旧格式：兼容处理
        # 摘要部分
        if "summary" in content_data and content_data["summary"]:
            blocks.append(self._create_heading_block("📝 核心摘要", level=2))
            blocks.append(self._create_text_block(str(content_data["summary"])))

        # 关键点部分
        if "key_points" in content_data and content_data["key_points"]:
            blocks.append(self._create_heading_block("💡 关键复盘", level=2))
            for point in content_data["key_points"]:
                if point:
                    blocks.append(self._create_bullet_block(point))

        # 详细逻辑
        if "logic_flow" in content_data and content_data["logic_flow"]:
            blocks.append(self._create_heading_block("📈 逻辑推演", level=2))
            blocks.append(self._create_text_block(str(content_data["logic_flow"])))

        return blocks

    def _convert_blocks_to_feishu_format(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将通用 block 格式转换为飞书 DocX block"""
        feishu_blocks = []

        for block in blocks:
            block_type = block.get("type", "text")
            content = block.get("content", "")

            if block_type == "heading_1":
                feishu_blocks.append(self._create_heading_block(content, level=1))
            elif block_type == "heading_2":
                feishu_blocks.append(self._create_heading_block(content, level=2))
            elif block_type == "heading_3":
                feishu_blocks.append(self._create_heading_block(content, level=3))
            elif block_type == "text":
                if content.strip():
                    feishu_blocks.append(self._create_text_block(content))
            elif block_type == "callout":
                if content.strip():
                    feishu_blocks.append(self._create_text_block(f"💡 {content}"))
            elif block_type == "bullet_list":
                feishu_blocks.append(self._create_bullet_block(content))
            elif block_type == "ordered_list":
                if content.strip():
                    feishu_blocks.append(self._create_text_block(f"1. {content}"))
            elif block_type == "divider":
                feishu_blocks.append(self._create_text_block("---"))
            elif block_type == "table":
                # 表格仍然降级为文本处理，因为 DocX 表格构建较复杂
                headers = block.get("headers", [])
                rows = block.get("rows", [])
                if headers and rows:
                    table_text = self._format_table(headers, rows)
                    feishu_blocks.append(self._create_text_block(table_text))

        return feishu_blocks

    def _create_text_block(self, text: str) -> Dict:
        """创建普通文本块 (Type=2)"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": text}}]
            }
        }

    def _create_heading_block(self, text: str, level: int) -> Dict:
        """创建标题块 (Type=3~9)"""
        # mapping: level 1 -> type 3, level 2 -> type 4, etc.
        block_type = 2 + level 
        key = f"heading{level}"
        
        return {
            "block_type": block_type,
            key: {
                "elements": [{"text_run": {"content": text}}]
            }
        }

    def _create_bullet_block(self, text: str) -> Dict:
        """创建无序列表块 (Type=12)"""
        return {
            "block_type": 12,
            "bullet": {
                "elements": [{"text_run": {"content": text}}]
            }
        }
        
    def _format_table(self, headers: List[str], rows: List[List[str]]) -> str:
        """格式化表格为文本"""
        table_text = " | ".join(headers) + "\n"
        table_text += "-" * (len(" | ".join(headers))) + "\n"
        for row in rows:
            table_text += " | ".join(str(cell) for cell in row) + "\n"
        return table_text
