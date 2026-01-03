import logging
import os
import sys

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.feishu_renderer.feishu_renderer import FeishuRenderer
from src.utils.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)


def main():
    try:
        # Load configuration
        config = Config()

        # Check if feishu config exists
        if not config.get("feishu.app_id") or not config.get("feishu.app_secret"):
            print("Error: Feishu configuration missing. Please check config.yaml or environment variables.")
            return

        print(f"Initializing Feishu Renderer with App ID: {config.get('feishu.app_id')}")
        renderer = FeishuRenderer(config)

        # Create sample content
        content_data = {
            "title": "测试云文档生成功能",
            "summary": "这是一个自动化测试生成的文档，用于验证Feishu Renderer的功能。",
            "tags": ["测试", "自动化", "Feishu"],
            "blocks": [
                {"type": "heading_1", "content": "测试报告"},
                {
                    "type": "callout",
                    "content": "这是一个高亮提示块 (Callout)",
                    "style": "blue",
                },
                {
                    "type": "text",
                    "content": "下面是一些普通文本内容。验证基本的文本渲染功能是否正常。",
                },
                {"type": "heading_2", "content": "列表测试"},
                {"type": "bullet", "content": "第一点"},
                {"type": "bullet", "content": "第二点"},
                {"type": "heading_2", "content": "表格测试"},
                {
                    "type": "table",
                    "headers": ["列1", "列2", "列3"],
                    "rows": [
                        ["数据1-1", "数据1-2", "数据1-3"],
                        ["数据2-1", "数据2-2", "数据2-3"],
                    ],
                },
            ],
        }

        print("Creating document and sending notification...")
        doc_url = renderer.render_content(content_data)

        if doc_url:
            print("SUCCESS: Document created and notification sent successfully!")
            print(f"Document URL: {doc_url}")
        else:
            print("FAILURE: Failed to create document or send notification.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
