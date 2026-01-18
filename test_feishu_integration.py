import os
import sys
import re
from pathlib import Path

# 确保能找到 src 目录
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from src.utils.config import Config
from src.utils.logger import get_logger
from src.feishu_renderer.document_renderer import DocumentRenderer
from src.feishu_renderer.block_builder import BlockBuilder
from src.feishu_renderer.feishu_client import FeishuClient

# --- 1. 定义支持富文本的自定义 Builder ---
class RichTextBlockBuilder(BlockBuilder):
    """
    扩展的 BlockBuilder，支持简单的 Markdown 内联样式（如 **加粗**）
    """
    def _parse_inline_elements(self, text: str) -> list:
        """
        解析文本中的 **加粗** 语法，返回飞书 elements 列表
        """
        elements = []
        # 正则匹配 **bold**
        parts = re.split(r'(\*\*.*?\*\*)', text)
        
        for part in parts:
            if not part:
                continue
            
            if part.startswith('**') and part.endswith('**') and len(part) > 4:
                # 是加粗文本
                content = part[2:-2]
                elements.append({
                    "text_run": {
                        "content": content,
                        "text_style": {"bold": True}
                    }
                })
            else:
                # 是普通文本
                elements.append({
                    "text_run": {
                        "content": part
                    }
                })
        return elements

    def _build_text(self, content: str) -> dict:
        """重写文本构建逻辑，使用富文本元素"""
        # 修正点：飞书文档 Text Block 类型为 2 (不是 1)
        # 类型 1 是 Page，不能作为子块创建，会导致 1770029 错误
        return {
            "block_type": 2, 
            "text": {
                "elements": self._parse_inline_elements(content)
            }
        }

    def _build_bullet(self, content: str) -> dict:
        """重写无序列表构建逻辑"""
        # 飞书文档 Bullet Block 类型为 12
        return {
            "block_type": 12,
            "bullet": {
                "elements": self._parse_inline_elements(content)
            }
        }
    
    # 标题也支持一下加粗解析
    def _build_heading_1(self, content: str) -> dict:
        return {"block_type": 3, "heading1": {"elements": self._parse_inline_elements(content)}}
    
    def _build_heading_2(self, content: str) -> dict:
        return {"block_type": 4, "heading2": {"elements": self._parse_inline_elements(content)}}
    
    def _build_heading_3(self, content: str) -> dict:
        return {"block_type": 5, "heading3": {"elements": self._parse_inline_elements(content)}}

# --- 2. Markdown 解析器 ---
def parse_markdown_to_blocks(md_text):
    """
    解析 Markdown 文本为 Block 结构信息
    """
    blocks = []
    lines = md_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('# '):
            blocks.append({"type": "heading_1", "content": line[2:].strip()})
        elif line.startswith('## '):
            blocks.append({"type": "heading_2", "content": line[3:].strip()})
        elif line.startswith('### '):
            blocks.append({"type": "heading_3", "content": line[4:].strip()})
        elif line.startswith('- ') or line.startswith('* '):
             blocks.append({"type": "bullet", "content": line[2:].strip()})
        else:
            blocks.append({"type": "text", "content": line})
            
    return blocks

def extract_title(md_text):
    """提取第一行作为标题，如果第一行是 # 开头则去除"""
    lines = md_text.split('\n')
    for line in lines:
        line = line.strip()
        if line:
            if line.startswith('# '):
                return line[2:].strip()
            return line
    return "未命名复盘文档"

# --- 3. 主程序 ---
def main():
    logger = get_logger()
    
    # 初始化配置
    try:
        config_loader = Config()
        app_id = config_loader.get("feishu.app_id")
        app_secret = config_loader.get("feishu.app_secret")
        webhook_url = config_loader.get("feishu.webhook")
        
        if not all([app_id, app_secret, webhook_url]):
            logger.error("❌ 缺少飞书配置")
            return
    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        return

    # 读取文件
    md_file_path = "cleaned_transcript_output.md"
    if not os.path.exists(md_file_path):
        # 尝试使用备用文件
        if os.path.exists("investment_diary_output.md"):
            md_file_path = "investment_diary_output.md"
        else:
            logger.error("❌ 未找到输入文件")
            return

    with open(md_file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 提取关键信息
    doc_title = extract_title(full_text)
    blocks = parse_markdown_to_blocks(full_text)
    
    logger.info(f"📄 提取文档标题: {doc_title}")

    # 构造数据
    content_data = {
        "title": doc_title,
        "summary": "本次复盘详细记录了市场概况、持仓变动及深度逻辑分析。",
        "blocks": blocks
    }

    try:
        # 初始化客户端
        feishu_config = {"app_id": app_id, "app_secret": app_secret}
        client = FeishuClient(feishu_config)
        
        # 初始化渲染器
        renderer = DocumentRenderer(config_loader)
        
        # 🔥 关键步骤：替换为我们自定义的 RichTextBlockBuilder
        renderer.builder = RichTextBlockBuilder()
        renderer.client = client # 确保 client 被正确更新

        logger.info("🚀 开始生成飞书文档（富文本模式）...")
        
        # 渲染文档
        doc_url = renderer.render_document(content_data)
        
        if doc_url:
            logger.info(f"✅ 文档生成成功: {doc_url}")
            
            # 发送优化后的卡片消息
            logger.info("🚀 发送群通知...")
            
            card_message = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "template": "blue",
                        "title": {
                            "tag": "plain_text",
                            "content": "📈 " + doc_title  # 在卡片标题中直接显示“第X天记录”
                        }
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**复盘摘要**：\n{content_data['summary']}\n\n已成功同步至飞书文档，点击下方按钮查看详情。"
                            }
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "查看完整复盘文档"
                                    },
                                    "url": doc_url,
                                    "type": "primary"
                                }
                            ]
                        }
                    ]
                }
            }
            
            client.send_webhook_message(webhook_url, card_message)
            logger.info("✅ 通知发送成功")
            
        else:
            logger.error("❌ 文档生成失败")

    except Exception as e:
        logger.error(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()