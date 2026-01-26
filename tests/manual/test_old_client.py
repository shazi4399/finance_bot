"""
使用旧的feishu_client测试
"""
from src.utils.config import Config
from src.utils.logger import setup_logger
from src.feishu_renderer.feishu_client import FeishuClient

def test_old_client():
    logger = setup_logger(name="test_old_client")

    # 加载配置
    config = Config("config.yaml")
    feishu_config = {
        "app_id": config.get("feishu.app_id"),
        "app_secret": config.get("feishu.app_secret")
    }

    client = FeishuClient(feishu_config)

    # 创建文档
    logger.info("创建文档...")
    doc_id = client.create_document("测试文档-旧客户端")
    logger.info(f"文档创建成功: {doc_id}")

    # 添加简单的文本块
    logger.info("添加文本块...")
    blocks = [
        {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": "这是一个测试文本"}}]
            }
        }
    ]

    success = client.add_blocks(doc_id, blocks)
    if success:
        logger.info("✅ 测试成功!")
        logger.info(f"文档链接: {client.get_document_url(doc_id)}")
    else:
        logger.error("❌ 添加块失败")

if __name__ == "__main__":
    test_old_client()
