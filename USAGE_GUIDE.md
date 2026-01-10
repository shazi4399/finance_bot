# Finance Bot 使用指南

## 📖 目录
1. [项目简介](#项目简介)
2. [功能特性](#功能特性)
3. [配置说明](#配置说明)
4. [使用流程](#使用流程)
5. [故障排查](#故障排查)
6. [API配置指南](#api配置指南)

---

## 🎯 项目简介

Finance Bot 是一个企业级自动化内容情报流水线系统，用于从B站财经视频中提取关键信息，生成结构化的投资复盘报告并发送到飞书。

**核心流程**：
```
B站视频 → 音频提取 → 语音转文字 → LLM智能分析 → 飞书文档 → 群消息通知
```

---

## ✨ 功能特性

### 1. 智能语音转文字
- ✅ 使用阿里云听悟 API（paraformer-v2 模型）
- ✅ 自动识别说话人（最多10人）
- ✅ 精确时间戳（精确到秒）
- ✅ 中英双语支持
- ✅ 高置信度转录（95%+）

### 2. LLM内容分析
- ✅ 提取持仓变动（标的、操作、详情、逻辑）
- ✅ 提取核心金句
- ✅ 生成精修全文逐字稿
- ✅ 智能段落分隔
- ✅ 保留原话真实性

### 3. 飞书文档渲染
- ✅ 精美排版，包含：
  - 视频信息卡片
  - 内容摘要
  - 持仓变动表格
  - 核心金句展示
  - 精修全文逐字稿（智能分段）
  - 带时间戳的原始转录
- ✅ 自动发送飞书群消息

---

## ⚙️ 配置说明

### 配置文件：`config.yaml`

```yaml
# 飞书配置
feishu:
  app_id: "cli_xxxxxx"          # 飞书应用ID
  app_secret: "xxxxx"            # 飞书应用密钥
  webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"  # 飞书群机器人webhook

# 阿里云配置
aliyun:
  access_key_id: "LTAI..."       # 阿里云AccessKey ID
  access_key_secret: "xxxxx"     # 阿里云AccessKey Secret
  oss_endpoint: "oss-cn-shanghai.aliyuncs.com"
  oss_bucket: "your-bucket"      # OSS存储桶名称
  region: "cn-shanghai"

# 通义千问配置
dashscope:
  api_key: "sk-xxxxx"            # DashScope API Key

# 通义听悟配置
tingwu:
  app_key: "xxxxx"               # 听悟应用Key（重要！）

# 监听目标配置
monitoring:
  bilibili_uid: "322005137"      # B站UP主UID
  check_interval: 3600           # 检查间隔（秒）
  max_videos_per_check: 5        # 每次处理视频数
  cookies_file: "data/bilibili_cookies.txt"  # B站cookies（可选）

# 文件存储配置
storage:
  temp_dir: "/tmp/finance_bot"
  oss_prefix: "daily_transcribe"
  cleanup_after_days: 1

# 日志配置
logging:
  level: "INFO"
  file: "logs/pipeline.log"
  max_size: "10MB"
  backup_count: 5

# 重试配置
retry:
  max_attempts: 3
  backoff_factor: 2
```

---

## 🚀 使用流程

### 方式一：完整流程（首次测试）

```bash
# 1. 从B站下载视频并上传到OSS
uv run python download_and_upload.py --bvid BV1xx411c7mD

# 2. 运行完整流程测试
uv run python test_improved_features.py
```

### 方式二：快速测试（使用已有OSS URL）

```bash
# 直接使用保存的OSS URL测试
uv run python test_improved_features.py

# 或手动指定OSS URL
uv run python test_improved_features.py --oss-url "https://your-bucket.oss-cn-shanghai.aliyuncs.com/..."
```

### 方式三：模拟数据测试（跳过语音转文字）

```bash
# 当听悟API配置有问题时，使用模拟数据测试其他功能
uv run python test_mock_data.py
```

### 方式四：生产环境运行

```bash
# 监控模式：自动检测新视频并处理
uv run python main.py

# 手动处理单个视频
uv run python cli_tool.py process --bvid BV1xx411c7mD
```

---

## 📁 输出文件

测试完成后会生成以下文件：

- `last_oss_url.txt` - OSS音频URL（用于后续测试）
- `test_transcript_result.json` - 完整转录结果（含时间戳和说话人）
- `test_content_result.json` - LLM分析结果
- `test_feishu_url.txt` - 飞书文档链接
- `logs/pipeline.log` - 运行日志

---

## 🔧 故障排查

### 1. 听悟API错误：`Invalid app key`

**问题**：配置的听悟 App Key 无效

**解决方案**：
1. 登录 [阿里云控制台](https://console.aliyun.com/)
2. 进入"智能语音交互" → "听悟服务"
3. 创建应用并获取 App Key
4. 更新 `config.yaml` 中的 `tingwu.app_key`

### 2. 飞书文档创建失败

**可能原因**：
- 飞书 App ID/Secret 配置错误
- 飞书应用权限不足

**解决方案**：
1. 检查飞书应用配置
2. 确保应用有"创建文档"和"发送消息"权限
3. 重新获取 Access Token

### 3. OSS上传失败

**可能原因**：
- OSS配置错误
- 网络问题
- 权限不足

**解决方案**：
1. 检查 `aliyun.access_key_id` 和 `access_key_secret`
2. 确认 OSS Bucket 存在且有写入权限
3. 检查网络连接

### 4. B站视频下载失败

**可能原因**：
- 视频需要登录
- 地区限制

**解决方案**：
1. 配置 `cookies_file` 参数
2. 从浏览器导出 B站 cookies
3. 保存到 `data/bilibili_cookies.txt`

---

## 🔑 API配置指南

### 阿里云听悟 (Tingwu)

1. 访问 [阿里云智能语音交互控制台](https://nls-portal.console.aliyun.com/)
2. 选择"听悟服务"
3. 创建应用
4. 获取 **App Key**
5. 更新到 `config.yaml` 的 `tingwu.app_key`

### 通义千问 (DashScope)

1. 访问 [DashScope控制台](https://dashscope.console.aliyun.com/)
2. 创建API Key
3. 更新到 `config.yaml` 的 `dashscope.api_key`

### 阿里云 OSS

1. 访问 [OSS控制台](https://oss.console.aliyun.com/)
2. 创建 Bucket
3. 获取 AccessKey ID 和 Secret
4. 更新到 `config.yaml` 的 `aliyun` 部分

### 飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 配置权限：
   - `docx:document:create` - 创建文档
   - `docx:document:write` - 编辑文档
   - `im:message:send` - 发送消息
5. 创建群机器人并获取 Webhook URL
6. 更新到 `config.yaml` 的 `feishu` 部分

---

## 📊 飞书文档结构

生成的飞书文档包含以下部分：

1. **视频信息** (蓝色卡片)
   - BVID
   - 上传时间
   - 视频链接

2. **内容摘要** (绿色卡片)
   - 200字核心概览
   - 当日盈亏
   - 市场定性

3. **持仓变动表格**
   - 标的名称
   - 操作类型（加仓/减仓/锁仓）
   - 仓位详情
   - 投资逻辑

4. **核心金句** (黄色卡片)
   - 提取原话
   - 保留通俗比喻

5. **全文逐字稿**（精修版）
   - 智能分段
   - 修正标点
   - 保留原话和口癖

6. **原始转录**（含时间戳）
   - [MM:SS] 格式时间戳
   - 说话人标识
   - 便于定位视频位置

7. **Footer**
   - 生成时间
   - 处理信息

---

## 💡 最佳实践

1. **首次测试**：使用 `test_mock_data.py` 验证飞书配置
2. **配置听悟 App Key** 后，使用 `download_and_upload.py` 测试完整流程
3. **保存 OSS URL**：首次上传后会保存到 `last_oss_url.txt`，后续测试可直接使用
4. **监控日志**：查看 `logs/pipeline.log` 了解详细执行情况
5. **定期清理**：OSS会自动清理1天前的文件，避免存储费用

---

## 🆘 获取帮助

- **查看日志**：`tail -f logs/pipeline.log`
- **测试配置**：`uv run python check_config.py`
- **GitHub Issues**：提交问题到项目仓库

---

## 📝 更新日志

### v1.1.0 (2024-01-04)
- ✨ 优化语音转文字功能，获取完整转录数据
- ✨ 大幅改进飞书文档排版
- ✨ 添加带时间戳的原始转录
- ✨ 增强错误处理和重试机制
- 🐛 修复听悟 App Key传递问题

### v1.0.0 (2023-12-01)
- 🎉 初始版本发布

---

**祝使用愉快！** 🎉
