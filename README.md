# Content Intelligence Pipeline
企业级自动化内容情报流水线

从非结构化媒体流到飞书结构化知识库的端到端实现

## 功能特性

- 🎥 **Bilibili视频监控**: 自动监控指定UP主的最新视频更新
- 🎵 **音频提取**: 智能提取视频音频并转换为MP3格式
- ☁️ **云存储**: 阿里云OSS作为中间态存储，支持断点续传
- 🎯 **语音转写**: 通义听悟API实现高精度语音识别和说话人分离
- 🧠 **内容分析**: 通义千问大模型进行语义结构化提取
- 📄 **文档生成**: 飞书Block架构生成精美结构化文档
- 📢 **即时通知**: Webhook发送交互式卡片消息

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd finance_bot

# 安装 uv (如果尚未安装)
# curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync
```

### 2. 配置设置

```bash
# 复制配置模板
cp config.yaml config.yaml.local
cp .env.example .env

# 编辑配置文件，填入你的API密钥
vim config.yaml.local
vim .env
```

### 3. 运行方式

```bash
# 验证配置
uv run main.py --config config.yaml.local --validate-config

# 单次运行
uv run main.py --config config.yaml.local --check-once

# 守护进程模式
uv run main.py --config config.yaml.local --daemon
```

## 配置说明

### 必需配置项

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| feishu.app_id | 飞书应用ID | 飞书开放平台 |
| feishu.app_secret | 飞书应用密钥 | 飞书开放平台 |
| aliyun.access_key_id | 阿里云AK ID | 阿里云控制台 |
| aliyun.access_key_secret | 阿里云AK Secret | 阿里云控制台 |
| aliyun.oss_bucket | OSS存储桶名称 | 阿里云OSS控制台 |
| dashscope.api_key | 通义千问API密钥 | 阿里云百炼平台 |
| tingwu.app_key | 通义听悟AppKey | 阿里云听悟控制台 |
| monitoring.bilibili_uid | 监听的B站UID | B站用户主页 |

### 可选配置项

- `monitoring.check_interval`: 检查间隔（秒，默认3600）
- `monitoring.max_videos_per_check`: 每次检查最多处理视频数
- `storage.cleanup_after_days`: OSS文件保留天数
- `logging.level`: 日志级别（DEBUG/INFO/WARNING/ERROR）

## 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Bilibili      │    │   Aliyun OSS    │    │  Tongyi Tingwu  │
│   Video Monitor │───▶│   Storage       │───▶│   ASR Service   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Feishu        │    │   Tongyi Qwen   │    │                 │
│   Notification  │◀───│   LLM Analysis  │◀───│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 项目结构

```
finance_bot/
├── src/
│   ├── downloader/          # 视频下载模块
│   ├── transcriber/         # 语音转写模块
│   ├── llm_processor/       # LLM内容分析模块
│   ├── feishu_renderer/     # 飞书文档渲染模块
│   ├── utils/              # 工具模块
│   └── pipeline.py         # 流水线编排
├── tests/                  # 测试文件
├── logs/                   # 日志文件
├── config.yaml            # 配置文件
├── pyproject.toml         # 项目依赖配置
├── uv.lock                # 依赖锁定文件
└── main.py               # 主入口
```

## 开发指南

### 添加新的处理器

1. 在对应模块目录下创建新的处理器类
2. 继承基础处理器接口
3. 实现 `process()` 方法
4. 在 `pipeline.py` 中注册新处理器

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python main.py --config config.yaml.local --check-once
```

## 故障排除

### 常见问题

1. **B站下载失败**: 检查cookies配置，确保已登录B站
2. **OSS上传失败**: 验证AK权限和Bucket配置
3. **听悟转写失败**: 检查音频格式和AppKey有效性
4. **飞书API失败**: 确认应用权限和Token有效性

### 日志查看

```bash
# 查看实时日志
tail -f logs/pipeline.log

# 查看错误日志
grep ERROR logs/pipeline.log
```

## 许可证

MIT License

## 贡献指南

欢迎提交Issue和Pull Request！