# debug_feishu.py
# 用法: uv run debug_feishu.py
import os
from src.utils.config import Config
from src.feishu_renderer.feishu_renderer import FeishuRenderer

def test_feishu_write():
    print("🚀 开始飞书写入测试...")
    
    # 1. 加载配置
    config = Config("config.yaml")
    renderer = FeishuRenderer(config)
    
    # 2. 模拟 LLM 生成的完美数据
    mock_data = {
        "summary": "这是一个测试摘要，用于验证飞书 API 是否正常写入。",
        "key_points": [
            "测试点 1: 确保 BlockBuilder 正常工作",
            "测试点 2: 确保 CreateChildren 接口调用成功",
            "测试点 3: 确保权限范围 (Scope) 包含 '编辑文档'"
        ],
        "logic_flow": "如果能看到这段文字，说明 '文档创建' -> '内容写入' 的链路已经打通。"
    }
    
    mock_video = {"title": "🤖 飞书写入连通性测试_v1"}
    
    # 3. 执行渲染
    url = renderer.render_content(mock_data, mock_video)
    
    if url:
        print(f"\n🎉 测试成功！请访问文档查看内容:\n{url}")
    else:
        print("\n❌ 测试失败，请检查日志输出。")

if __name__ == "__main__":
    test_feishu_write()