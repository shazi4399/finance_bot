import sys
import os
from pathlib import Path
import dashscope
from dashscope import Generation
from src.utils.config import Config

# 1. 环境配置
# 确保能找到 src 目录
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    config = Config()
    api_key = config.get("dashscope.api_key")
    if not api_key:
        raise ValueError("未在配置文件或环境变量中找到 dashscope.api_key")
    dashscope.api_key = api_key
    print(f"✅ API Key 加载成功")
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    sys.exit(1)

# 2. 定义通用股票池 (用于辅助模型纠错)
# 这是一个提示性的列表，模型会根据这个列表+上下文逻辑去推理
stock_universe = [
    "蒙牛乳业", "长实集团", "长和", "同仁堂国药", "同仁堂科技", 
    "神威药业", "百胜中国", "海底捞", "民航信息网络", "中国国航",
    "南方航空", "东方航空", "腾讯控股", "美团", "小米集团", 
    "快手", "中芯国际", "天津发展", "电能实业", "长江基建", 
    "白云山", "达仁堂", "华润医药", "复星医药", "中国移动"
]

# 3. 读取原始 ASR 文件
file_path = "result_diarization_mode.txt"
output_file = "cleaned_transcript_output.md"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    print(f"✅ 成功读取原文，长度: {len(raw_text)} 字")
except FileNotFoundError:
    print(f"❌ 未找到文件: {file_path}")
    sys.exit(1)

# 4. 构建“原文清洗”专用 Prompt
system_prompt = f"""
你是一位拥有20年经验的**专业财经书籍编辑和股票投资者**。
你的任务是将一份粗糙的语音转录文本（ASR），精修成一篇**流畅、专业、易读的文章**。

【核心任务：清洗与重构】
请对原文进行“无损润色”，要求如下：

1. **ASR 实体智能修正 (最重要)**：
   - 原始文本中充满了同音错别字（如将股票名识别为奇怪的词）。
   - 请参考以下【常见关注标的】，结合**读音相似性**和**金融上下文**进行修正：
   - 列表：{", ".join(stock_universe)}
   - *示例规则*：听到“猛将”修正为“蒙牛”，听到“常识”修正为“长实”，听到“百盛”修正为“百胜”。

2. **口语转书面语**：
   - 删除口语废话（如“然后”、“那个”、“对吧”、“就是说”）。
   - 修复标点符号，将破碎的短句合并为通顺的长句。
   - 保持讲者“史诗级韭菜”的个人风格（真诚、实战派），不要改写成冷冰冰的新闻稿。

3. **完整性保留 (严禁删减)**：
   - 这不是总结，是**精修**。请保留原文中所有的**财务数据**（股价、毛利、仓位金额）、**具体操作细节**和**逻辑推演过程**。
   - 不要遗漏任何一个观点
   - 文中的汉字尽量用阿拉伯数字表示，例如6个点请用6%表示。

4. **排版优化**：
   - 根据语义逻辑，将长文本切分为合理的段落。
   - 可以在段落前加上【小标题】以提升阅读体验（可选）。
   - 关键的股票名称和核心数据（如金额、百分比）请使用 **加粗** 标注。

【输入文本处理】
请直接输出精修后的正文，不需要任何开场白。
"""

user_prompt = f"""
请清洗以下文本：

{raw_text}
"""

# 5. 调用 Qwen-Max
print("\n🚀 正在调用 Qwen-Max 进行全文精修，这可能需要几十秒...\n")

try:
    response = Generation.call(
        model='qwen-max', 
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        result_format='message',
        temperature=0.3, # 较低温度，确保纠错的准确性
    )

    if response.status_code == 200:
        cleaned_content = response.output.choices[0].message.content
        
        # 打印部分预览
        print("="*50)
        print("📝 精修预览 (前500字)：\n")
        print(cleaned_content[:500] + "...\n")
        print("="*50)
        
        # 保存文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        print(f"\n✅ 完整精修版已保存至: {output_file}")
        
    else:
        print(f"❌ API 调用失败: {response.code} - {response.message}")

except Exception as e:
    print(f"❌ 运行出错: {e}")