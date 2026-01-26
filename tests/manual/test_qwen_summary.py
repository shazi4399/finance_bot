import os
import sys
from pathlib import Path
import dashscope
from dashscope import Generation
from src.utils.config import Config

# 1. 初始化配置
# 确保能找到 src 目录
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    config = Config()
    api_key = config.get("dashscope.api_key")
    if not api_key:
        raise ValueError("未在配置文件或环境变量中找到 dashscope.api_key")
    dashscope.api_key = api_key
    print(f"✅ 成功加载 API Key: {api_key[:8]}******")
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    sys.exit(1)

# 2. 定义股票池 (这是核心逻辑)
# 您可以随时在这里添加新的关注标的
stock_universe = [
    "蒙牛乳业", "长实集团", "长和", "同仁堂国药", "同仁堂科技", 
    "神威药业", "百胜中国", "海底捞", "民航信息网络", "中国国航",
    "南方航空", "东方航空", "腾讯控股", "美团", "小米集团", 
    "快手", "中芯国际", "天津发展", "电能实业", "长江基建", 
    "白云山", "达仁堂", "华润医药"
]

# 3. 读取源文件
file_path = "result_diarization_mode.txt"  # 假设文件在当前目录下
try:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    print(f"✅ 成功读取文件，长度: {len(raw_text)}")
except FileNotFoundError:
    print(f"❌ 未找到文件: {file_path}")
    # 如果没找到文件，使用一个模拟片段进行测试
    print("⚠️ 将使用模拟文本进行测试...")
    raw_text = "Hello各位小伙伴，我是史诗级韭菜。今天猛将乳液涨了不少，但我把常识卖了一点。沈巍药业还是比较稳的。"

# 4. 构建 Prompt
# 4. 🔥 核心：通用化 System Prompt 🔥
system_prompt = f"""
你是一位拥有20年经验的**首席投资顾问**和**专业财经编辑**。
你的任务是将一段语音转录文本（ASR），整理成一篇**极具深度、细节详实**的《投资复盘深度研报》。

【核心原则：通用逻辑还原】
请忽略具体的标的名称差异，而是专注于提取以下**三类核心信息**：

1. **交易行为模式识别 (Action Pattern)**：
   - 凡是文中提到“买入、卖出、加仓、减仓、做T、锁仓”的地方，必须提取出来。
   - **关键细节**：必须保留操作的**价格点位**、**仓位变化**（如“卖了多少”、“剩多少”）以及**成本变化**（如“成本压到了XX”）。

2. **数据锚点提取 (Data Anchor)**：
   - **严禁删减数字**：文中出现的所有**财务数据**（毛利率、净利率、ROE、负债率、现金流）、**估值数据**（PE、PB、分位点）和**价格数据**必须完整保留并**加粗**。
   - 如果博主进行了数据对比（如“A公司比B公司便宜”），请完整保留对比逻辑。

3. **投资逻辑推演 (Thesis Extraction)**：
   - 提取博主对一家公司的**定性分析**（如“商业模式”、“资产负债表质量”、“管理层人品”）。
   - 还原**因果链条**：为什么认为它便宜？为什么认为它安全？（不要只写结论，要写推导过程）。

【ASR 智能纠错】
文中可能包含股票名称的同音错误。请参考以下【关注股票池】进行上下文智能修正，但**不要局限于此列表**，遇到列表外的知名股票也许根据通用金融知识修正：
{", ".join(stock_universe)}

【文章结构标准】
请严格按照以下**通用模板**输出，无论博主讨论的是什么股票：

### 1. 市场概况与策略
* **账户状态**：市值、盈亏、资金变动。
* **宏观/情绪**：博主对大盘（恒指/A股）及时间节点（如年底/财报季）的思考。

### 2. 重点持仓操作详解 (Operational Review)
* **自动聚合**：将文中分散提到的同一只股票的操作整合到一个条目下。
* **格式**：
    * **[股票名称]**
        * **操作**：{{"买卖方向"}} @ {{"具体价格/时机"}}
        * **逻辑**：{{"为什么这么做？"}}
        * **状态**：{{"当前持仓/成本变化"}}

### 3. 深度个股分析 (Deep Dive)
* 针对文中**篇幅最长、分析最细**的1-2个标的进行深度展开。
* **基本面画像**：列出博主提到的所有财务指标（毛利/净利/负债/现金）。
* **核心看点**：用子标题列出逻辑（如“**资产负债表极佳**”、“**商业模式特质**”）。

### 4. 总结与投资哲学
* 提取博主的方法论总结（选股因子、长期策略）。

【格式要求】
* 保持哔哩哔哩博主“史诗级韭菜”的个人人设（真诚、实战派、龟龟投资流）。
* **长文模式**：宁可多写细节，不要过度概括。
"""

user_prompt = f"""
请根据上述要求，整理以下录音文本：

{raw_text}
"""

# 5. 调用通义千问 API
print("\n🚀 正在请求 Qwen-Max 模型进行整理，请稍候...\n")

try:
    response = Generation.call(
        model='qwen-max', # 使用最强模型处理复杂逻辑
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        result_format='message',
        temperature=0.3, # 低温度保证数据准确性
    )

    if response.status_code == 200:
        content = response.output.choices[0].message.content
        print("="*50)
        print("📝 生成结果：\n")
        print(content)
        print("="*50)
        
        # 可选：保存结果到文件
        output_file = "investment_diary_output.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ 结果已保存至: {output_file}")
        
    else:
        print(f"❌ API 调用失败: {response.code} - {response.message}")

except Exception as e:
    print(f"❌ 发生错误: {e}")