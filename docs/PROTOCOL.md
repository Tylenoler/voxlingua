# VoxLingua 通信协议文档

> 定义手机端 (Flutter) 与电脑端 (Tauri + Python Sidecar) 之间的通信规范

## 1. 概述

手机与电脑通过**局域网 WiFi** 通信，使用 **WebSocket** 作为传输层，**mDNS** 作为设备自动发现协议。

## 2. 设备发现

### mDNS 服务注册

电脑端启动后，向局域网广播 mDNS 服务：

```
服务类型: _voxlingua._tcp
端口: 9876
TXT 记录:
  - version=1.0.0
  - device_name=VoxLingua-Desktop
  - status=running
```

### 手机端发现流程

```
手机开机/进入页面 → 搜索 _voxlingua._tcp
                     ↓
发现电脑 → 记录 IP:Port → 建立 WebSocket 连接
                     ↓
连接成功 → 进入就绪状态 → UI 显示"已连接到电脑"
```

## 3. WebSocket 消息协议

### 连接地址
```
ws://{desktop_ip}:9876/ws/mobile
```

### 消息帧格式

所有消息使用 JSON 编码的字符串帧：

```json
{
  "type": "<message_type>",
  "payload": { ... }
}
```

### 3.1 连接握手

**手机 → 电脑：**
```json
{
  "type": "handshake",
  "payload": {
    "client": "voxlingua-mobile",
    "version": "1.0.0",
    "platform": "android"  // 或 "ios"
  }
}
```

**电脑 → 手机：**
```json
{
  "type": "handshake_ack",
  "payload": {
    "session_id": "sess_abc123xyz",
    "server_version": "1.0.0",
    "supported_languages": ["en", "ja", "ko", "zh", "fr", "de"],
    "status": "ready"
  }
}
```

### 3.2 音频传输 (口语对练)

**手机 → 电脑：用户录音**
```json
{
  "type": "audio_input",
  "payload": {
    "session_id": "sess_abc123xyz",
    "format": "opus",           // 音频编码
    "sample_rate": 16000,       // 采样率
    "duration_ms": 2800,        // 录音时长
    "data": "<base64_encoded_audio>"
  }
}
```

**电脑 → 手机：AI 回复音频**
```json
{
  "type": "audio_output",
  "payload": {
    "session_id": "sess_abc123xyz",
    "format": "wav",
    "sample_rate": 24000,
    "data": "<base64_encoded_audio>",
    "text": "The original AI response text for display",
    "language": "en",
    "emotion": "friendly"
  }
}
```

### 3.3 评分结果

**电脑 → 手机：发音评分**
```json
{
  "type": "scoring_result",
  "payload": {
    "type": "pronunciation",           // 或 "conversation"
    "user_text": "the text user spoke",
    "target_text": "the expected text",
    "overall_score": 85.5,
    "dimensions": {
      "phoneme_accuracy": 88.0,
      "fluency": 82.0,
      "prosody": 85.0,
      "completeness": 90.0,
      "grammar": 87.0
    },
    "phoneme_errors": [
      {
        "phoneme": "θ",
        "expected": "θ",
        "actual": "s",
        "word": "think",
        "position": 0,
        "severity": "minor"
      }
    ],
    "feedback": "Good effort! Try placing your tongue between your teeth when saying 'th' sounds."
  }
}
```

### 3.4 控制消息

**手机 → 电脑：切换场景**
```json
{
  "type": "set_scene",
  "payload": {
    "session_id": "sess_abc123xyz",
    "scene": "restaurant",       // scene ID
    "language": "en",
    "difficulty": "intermediate" // beginner / intermediate / advanced
  }
}
```

**手机 → 电脑：切换声纹**
```json
{
  "type": "set_voice",
  "payload": {
    "session_id": "sess_abc123xyz",
    "voice_profile_id": "vp_morgan_freeman"
  }
}
```

**手机 → 电脑：单词练习**
```json
{
  "type": "vocab_practice",
  "payload": {
    "session_id": "sess_abc123xyz",
    "words": ["pronunciation", "vocabulary", "fluently"],
    "voice_profile_id": "vp_morgan_freeman"
  }
}
```

**电脑 → 手机：错误/状态**
```json
{
  "type": "error",
  "payload": {
    "code": "model_not_loaded",
    "message": "Voice clone model is loading, please wait..."
  }
}
```

## 4. REST API (辅助接口)

除了 WebSocket 长连接，电脑端也提供 HTTP REST API 供手机调用非实时操作：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取电脑运行状态、模型加载情况 |
| `/api/voices` | GET | 获取可用声纹列表 |
| `/api/scenes` | GET | 获取可用场景列表 |
| `/api/upload_voice` | POST | 上传声纹参考音频 |
| `/api/history` | GET | 获取对话历史记录 |
| `/api/vocabulary` | GET | 获取生词本 |

## 5. 音频编码规范

| 方向 | 编码 | 采样率 | 说明 |
|------|------|--------|------|
| 手机 → 电脑 | Opus | 16kHz | 压缩率高，适合实时传输用户录音 |
| 电脑 → 手机 | PCM WAV | 24kHz | 高质量播放，CosyVoice 原生输出 |
