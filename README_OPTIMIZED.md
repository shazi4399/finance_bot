# 财经视频内容情报流水线

自动化处理B站财经视频，生成结构化的每日复盘文档并发送到飞书群。

## 🎯 核心功能

1. **语音转文字**：使用阿里云通义听悟API，将视频音频转换为文字
2. **智能分析**：使用通义千问LLM提取关键信息（持仓变动、交易逻辑、核心金句）
3. **文档生成**：自动生成格式化的飞书文档
4. **群组通知**：通过飞书机器人将文档发送到指定群组

## 📋 优化亮点

### 1. 通义听悟优化
- ✅ 使用句子级别输出（`output_level=0`），避免词级别的碎片化
- ✅ 智能合并段落，按说话人分组
- ✅ 自动清理多余空格和重复标点

### 2. LLM分析优化
- ✅ 专门针对每日复盘内容设计的提示词
- ✅ 高保真提取：保留原话、数字、口癖
- ✅ 结构化输出：持仓变动、交易逻辑、核心金句

### 3. 飞书文档优化
- ✅ 清晰的卡片式布局
- ✅ 使用emoji和格式化增强可读性
- ✅ 分段展示：核心摘要、持仓变动、金句、全文逐字稿

## 🚀 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置文件

编辑 `config.yaml`：

```yaml
# 飞书配置
feishu:
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  webhook: "your_webhook_url"

# 阿里云配置
aliyun:
  access_key_id: "your_access_key_id"
  access_key_secret: "your_access_key_secret"
  oss_endpoint: "oss-cn-shanghai.aliyuncs.com"
  oss_bucket: "your_bucket_name"

# 通义千问配置
dashscope:
  api_key: "your_dashscope_api_key"

# 通义听悟配置
tingwu:
  app_key: "your_tingwu_app_key"
```

### 3. 测试运行

#### 方式1：从已转录的JSON文件测试（推荐，节省额度）

```bash
uv run test_from_json.py
```

#### 方式2：完整流程测试（包含上传和转录）

```bash
uv run test_full_pipeline.py <音频文件路径>
```

示例：
```bash
uv run test_full_pipeline.py BV1234567890.mp3
```

## 📁 项目结构

```
finance_bot/
├── src/
│   ├── transcriber/          # 语音转文字模块
│   │   ├── tingwu_client.py  # 通义听悟客户端（已优化）
│   │   └── transcriber.py    # 转写器封装
│   ├── llm_processor/        # LLM分析模块
│   │   ├── qwen_client.py    # 通义千问客户端
│   │   └── content_analyzer.py  # 内容分析器（已优化）
│   ├── feishu_renderer/      # 飞书渲染模块
│   │   ├── feishu_client.py  # 飞书API客户端
│   │   ├── feishu_renderer.py  # 文档渲染器
│   │   └── block_builder.py  # Block构建器（已优化）
│   └── utils/                # 工具模块
│       ├── config.py         # 配置管理
│       ├── logger.py         # 日志管理
│       └── storage.py        # OSS存储
├── test_from_json.py         # 从JSON测试（推荐）
├── test_full_pipeline.py     # 完整流程测试
└── config.yaml               # 配置文件
```

## 🔧 核心优化说明

### 通义听悟API参数优化

**问题**：默认的词级别输出（`output_level=1`）导致"两个字就一行"的碎片化问题

**解决方案**：
```python
# tingwu_client.py:71
transcription_param = tingwu_models.CreateTaskRequestParametersTranscription(
    diarization_enabled=True,  # 区分说话人
    output_level=0,            # 使用句子级别，避免碎片化 ✅
)
```

### 文本合并优化

**智能合并逻辑**：
- 按说话人分组段落
- 自动清理多余空格
- 去除重复标点
- 保持段落完整性

```python
# tingwu_client.py:189
def _smart_merge_words(self, words: List[Dict]) -> str:
    """智能合并词，处理标点和空格"""
    merged = "".join([w.get("Text", "") for w in words])
    merged = re.sub(r'\s+', '', merged)  # 移除所有空格
    merged = re.sub(r'([，。！？、；：])\1+', r'\1', merged)  # 去除重复标点
    return merged
```

### 飞书文档排版优化

**优化前**：所有内容混在一起，难以阅读

**优化后**：
- 📊 清晰的标题和分节
- 💡 核心摘要使用引用格式突出
- 📈 持仓变动使用卡片式布局
- 💬 金句使用引用格式
- 📝 全文逐字稿分段展示

## 📊 输出示例

生成的飞书文档包含：

1. **标题**：📊 2023-10-05 | 市场就像天气，说变就变
2. **今日核心**：200字以内的核心概览
3. **持仓变动与逻辑**：
   - 标的名称、操作类型
   - 具体仓位数据
   - 交易逻辑（保留原话）
4. **核心金句**：提取的精彩语录
5. **全文逐字稿**：LLM整理后的完整内容

## 🎯 使用场景

- 每日复盘记录自动化
- 财经视频内容提取
- 交易逻辑归档
- 投资决策回顾

## ⚠️ 注意事项

1. **节省额度**：使用 `test_from_json.py` 可以避免重复转录，节省阿里云额度
2. **API限制**：通义听悟有并发限制，建议控制任务提交频率
3. **文档权限**：确保飞书应用有文档编辑权限
4. **Webhook配置**：需要在飞书群中添加机器人并获取webhook地址

## 🔄 工作流程

```
音频文件 → OSS上传 → 通义听悟转写 → 通义千问分析 → 飞书文档生成 → 群组通知
```

## 📝 更新日志

### 2026-01-19
- ✅ 优化通义听悟API参数，使用句子级别输出
- ✅ 改进文本合并逻辑，解决碎片化问题
- ✅ 优化飞书文档排版，提升可读性
- ✅ 添加完整流程测试脚本
- ✅ 完善项目文档

## 📧 联系方式

如有问题或建议，请提交Issue。
