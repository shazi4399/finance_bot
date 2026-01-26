"""
测试最简单的飞书文档创建
"""
import lark_oapi as lark
from src.utils.config import Config
from src.utils.logger import setup_logger

def test_simple_doc():
    logger = setup_logger(name="test_simple")

    # 加载配置
    config = Config("config.yaml")
    app_id = config.get("feishu.app_id")
    app_secret = config.get("feishu.app_secret")

    # 初始化客户端
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.INFO) \
        .build()

    # 1. 创建文档
    logger.info("创建文档...")
    request = lark.docx.v1.CreateDocumentRequest.builder() \
        .request_body(lark.docx.v1.CreateDocumentRequestBody.builder()
            .title("测试文档-最简单")
            .build()) \
        .build()

    response = client.docx.v1.document.create(request)
    if not response.success():
        logger.error(f"创建文档失败: {response.code} - {response.msg}")
        return

    doc_id = response.data.document.document_id
    logger.info(f"文档创建成功: {doc_id}")

    # 2. 添加一个简单的文本块
    logger.info("添加文本块...")
    text_run = lark.docx.v1.TextRun.builder() \
        .content("这是一个测试文本") \
        .build()

    text_obj = lark.docx.v1.Text.builder() \
        .elements([text_run]) \
        .build()

    block = lark.docx.v1.Block.builder() \
        .block_type(2) \
        .text(text_obj) \
        .build()

    add_request = lark.docx.v1.CreateDocumentBlockChildrenRequest.builder() \
        .document_id(doc_id) \
        .block_id(doc_id) \
        .request_body(lark.docx.v1.CreateDocumentBlockChildrenRequestBody.builder()
            .children([block])
            .build()) \
        .build()

    add_response = client.docx.v1.document_block_children.create(add_request)
    if not add_response.success():
        logger.error(f"添加块失败: {add_response.code} - {add_response.msg}")
        logger.error(f"错误详情: {add_response.raw.content if hasattr(add_response.raw, 'content') else add_response.raw}")
        return

    logger.info("✅ 测试成功!")
    logger.info(f"文档链接: https://www.feishu.cn/docx/{doc_id}")

if __name__ == "__main__":
    test_simple_doc()
