# Testing Guide for Finance Bot

This guide explains how to test each component of the Content Intelligence Pipeline individually using the `cli_tool.py` script.

## Overview

The project consists of 4 main modules:
1. **Downloader**: Downloads video and extracts audio.
2. **Uploader**: Uploads audio to Aliyun OSS (required for transcription).
3. **Transcriber**: Transcribes audio using Tingwu API.
4. **Summarizer (LLM)**: Summarizes the transcript using Qwen LLM.
5. **Feishu Renderer**: Sends the summary to Feishu.

We have created `cli_tool.py` to allow you to run each of these steps manually and inspect the intermediate outputs.

## Prerequisites

Ensure your `config.yaml` is properly configured with:
- Bilibili UID and cookies (optional but recommended)
- Aliyun Access Key and Secret
- Tingwu App Key
- DashScope API Key (for Qwen)
- Feishu Webhook URL (if testing notification)

## Step-by-Step Testing

### 1. Test Downloader

Download a video and extract its audio.

```bash
python cli_tool.py download --bvid <BV_ID>
```

**Example:**
```bash
python cli_tool.py download --bvid BV1xx411c7mD
```

**Output:**
- An audio file (e.g., in `/tmp/finance_bot/`)
- A JSON file `<BV_ID>_info.json` containing video metadata.

### 2. Test Uploader

Upload the extracted audio file to OSS. This is a necessary step before transcription.

```bash
python cli_tool.py upload --file <PATH_TO_AUDIO_FILE>
```

**Output:**
- Prints the OSS URL of the uploaded file.

### 3. Test Transcriber

Transcribe the audio using the OSS URL.

```bash
python cli_tool.py transcribe --url <OSS_URL>
```

**Output:**
- `transcript.json`: The full transcription result.

### 4. Test Summarizer (LLM)

Process the transcript to generate a summary and structured content.

```bash
python cli_tool.py summarize --transcript transcript.json --video-info <BV_ID>_info.json
```

**Output:**
- `summary.json`: The structured content ready for Feishu.

### 5. Test Feishu Renderer

Render the content to a Feishu document.

```bash
python cli_tool.py feishu --content summary.json
```

**Output:**
- Prints the URL of the created Feishu document.

## Troubleshooting

- **Config Errors**: Ensure `config.yaml` exists and has all required fields.
- **Permission Errors**: Check your API keys and OSS permissions.
- **Path Errors**: Use absolute paths if relative paths are confusing.
