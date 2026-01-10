# 🚀 Finance Bot - 快速开始

## 📦 安装

```bash
# 确保安装了 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目（如果还没有）
cd finance_bot
```

## ⚙️ 配置

### 1. 配置 API 密钥

编辑 `config.yaml`，填入你的 API 密钥：

```yaml
# 飞书配置（必需）
feishu:
  app_id: "cli_xxxxxx"           # 从飞书开放平台获取
  app_secret: "xxxxx"
  webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"

# 阿里云配置（必需）
aliyun:
  access_key_id: "LTAI..."       # 从阿里云控制台获取
  access_key_secret: "xxxxx"
  oss_bucket: "your-bucket"      # 你的OSS bucket名称

# 通义千问（必需）
dashscope:
  api_key: "sk-xxxxx"            # 从DashScope控制台获取

# 通义听悟（必需）
tingwu:
  app_key: "xxxxx"               # ⚠️ 重要！从听悟控制台获取
```

### 2. 获取 API 密钥的链接

- **飞书**: https://open.feishu.cn/
- **阿里云 OSS**: https://oss.console.aliyun.com/
- **通义千问**: https://dashscope.console.aliyun.com/
- **通义听悟**: https://nls-portal.console.aliyun.com/

详细配置说明请查看 [USAGE_GUIDE.md](./USAGE_GUIDE.md#api配置指南)

## 🎯 使用

### 快速测试（推荐）

使用模拟数据测试飞书功能（无需配置听悟 App Key）：

```bash
uv run python test_mock_data.py
```

✅ 测试通过后会：
- 创建飞书文档
- 发送飞书群消息
- 显示文档链接

### 完整流程

```bash
# 一键运行完整流程
uv run python run.py --bvid BV1xx411c7mD
```

流程包括：
1. 📥 下载B站视频并提取音频
2. 📤 上传到OSS
3. 🎙️ 语音转文字（听悟API）
4. 🤖 LLM内容分析
5. 📄 生成飞书文档
6. 📨 发送群消息通知

### 分步测试

```bash
# 步骤 1: 下载并上传到OSS
uv run python download_and_upload.py --bvid BV1xx411c7mD

# 步骤 2: 测试语音转文字 + 飞书（使用保存的OSS URL）
uv run python test_improved_features.py
```

## 📄 查看结果

测试完成后：
1. 查看飞书文档链接（终端输出或 `last_feishu_url.txt`）
2. 检查飞书群是否收到消息
3. 查看生成的JSON文件：
   - `test_transcript_result.json` - 转录结果
   - `test_content_result.json` - 分析结果

## 🆘 故障排查

### 问题：听悟API错误 `Invalid app key`

**解决**：
1. 登录 https://nls-portal.console.aliyun.com/
2. 创建听悟应用
3. 获取正确的 App Key
4. 更新 `config.yaml` 中的 `tingwu.app_key`

**临时方案**：使用模拟数据测试
```bash
uv run python test_mock_data.py
```

### 问题：飞书文档创建失败

**检查**：
- 飞书 app_id 和 app_secret 是否正确
- 飞书应用是否有文档创建权限

### 问题：B站视频下载失败

**解决**：
- 视频可能需要登录
- 配置 `cookies_file` 参数
- 从浏览器导出B站cookies

## 📚 更多文档

- [完整使用指南](./USAGE_GUIDE.md) - 详细功能说明
- [API配置指南](./USAGE_GUIDE.md#api配置指南) - 各API获取方式
- [故障排查](./USAGE_GUIDE.md#故障排查) - 常见问题解决

## ✨ 主要功能

- ✅ 智能语音转文字（支持说话人识别）
- ✅ 提取持仓变动和投资逻辑
- ✅ 生成精修全文逐字稿
- ✅ 带时间戳的原始转录
- ✅ 精美的飞书文档排版
- ✅ 自动发送飞书群消息

## 💡 提示

1. **首次使用**：先运行 `test_mock_data.py` 测试飞书配置
2. **配置听悟**后：使用 `run.py` 运行完整流程
3. **节省流量**：首��上传后会保存 OSS URL，后续测试可跳过下载

---

**祝使用愉快！** 🎉

有问题？查看 [完整文档](./USAGE_GUIDE.md) 或查看日志 `logs/pipeline.log`
