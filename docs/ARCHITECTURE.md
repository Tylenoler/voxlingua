# VoxLingua 架构设计文档

## 1. 系统架构概览

### 双端通信架构

```
┌──────────────────────────────────────────────────────────────────┐
│  💻 Desktop App (Tauri v2)                                       │
│                                                                  │
│  ┌──────────────────────────────────────┐                       │
│  │  Tauri Main Process (Rust)            │                       │
│  │  ├── 窗口管理                          │                       │
│  │  ├── 系统托盘                            │                       │
│  │  ├── Sidecar 生命周期管理               │                       │
│  │  └── 本地文件系统 API                   │                       │
│  └──────────────┬───────────────────────┘                       │
│                 │  IPC (invoke)                                  │
│  ┌──────────────▼───────────────────────┐                       │
│  │  Frontend (React + TypeScript)        │                       │
│  │  ├── 对话界面 (Chat UI)                │                       │
│  │  ├── 声纹管理 (Voice Profile Manager)  │                       │
│  │  ├── 设置面板 (Settings)               │                       │
│  │  └── 本地仪表盘 (Dashboard)            │                       │
│  └──────────────────────────────────────┘                       │
│                                                                  │
│  ┌──────────────────────────────────────┐                       │
│  │  Python Sidecar (FastAPI)             │◄──── localhost:8765   │
│  │  ────────────────                     │                       │
│  │  [AI Engine Server]                   │                       │
│  │                                                                  │
│  │  ├── /api/stt        ← 语音转文字    │                       │
│  │  ├── /api/chat       ← 对话生成      │                       │
│  │  ├── /api/tts        ← 语音合成      │                       │
│  │  ├── /api/score      ← 发音评分      │                       │
│  │  ├── /api/voice-clone ← 声纹克隆     │                       │
│  │  └── /ws/mobile      ← 手机端 WebSocket │                    │
│  └──────────────────────────────────────┘                       │
└──────────────────────────┬───────────────────────────────────────┘
                           │ 局域网 WiFi
                           │ WebSocket / HTTP
┌──────────────────────────▼───────────────────────────────────────┐
│  📱 Mobile App (Flutter)                                         │
│                                                                  │
│  ┌──────────────────────────────────────┐                       │
│  │  Auto Discovery Layer (mDNS)         │                       │
│  │  自动搜索同一局域网内的 VoxLingua 桌面     │                       │
│  └──────────────────────────────────────┘                       │
│                                                                  │
│  ┌──────────────────────────────────────┐                       │
│  │  Communication Layer (WebSocket)     │                       │
│  │  ├── 发送录音音频 (Opus 编码)          │                       │
│  │  ├── 接收合成音频 (PCM/WAV)           │                       │
│  │  └── 收发 JSON 控制消息               │                       │
│  └──────────────────────────────────────┘                       │
│                                                                  │
│  ┌──────────────────────────────────────┐                       │
│  │  UI Layer                             │                       │
│  │  ├── 对话页面 (Chat Screen)           │                       │
│  │  ├── 录音界面 (Record Button)         │                       │
│  │  ├── 单词练习 (Vocab Practice)        │                       │
│  │  ├── 评分卡片 (Score Card)            │                       │
│  │  └── 设置页面 (Settings)              │                       │
│  └──────────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

## 2. 目录结构

```
voxlingua/
├── desktop/                         # Tauri 桌面应用
│   ├── src-tauri/                   # Rust 后端 (Tauri)
│   │   ├── src/
│   │   │   ├── main.rs              # 入口：启动 sidecar + 窗口
│   │   │   ├── sidecar.rs           # Python 进程管理
│   │   │   ├── commands.rs          # Tauri IPC 命令
│   │   │   └── discovery.rs         # mDNS 广播 (桌面端发现)
│   │   ├── Cargo.toml
│   │   └── tauri.conf.json
│   ├── src/                         # React 前端
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── VoiceProfileSelector.tsx
│   │   │   ├── ScoreCard.tsx
│   │   │   └── SettingsPanel.tsx
│   │   ├── hooks/
│   │   │   ├── useAIEngine.ts       # 与 Python sidecar 通信
│   │   │   └── useAudioRecorder.ts
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── tailwind.config.js
│   └── package.json
│
├── mobile/                          # Flutter 手机应用
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   │   ├── chat_screen.dart
│   │   │   ├── practice_screen.dart
│   │   │   └── settings_screen.dart
│   │   ├── services/
│   │   │   ├── websocket_service.dart
│   │   │   ├── discovery_service.dart  # mDNS 发现桌面
│   │   │   └── audio_service.dart
│   │   ├── models/
│   │   └── widgets/
│   └── pubspec.yaml
│
├── engine/                          # Python AI 引擎
│   ├── api/                         # FastAPI 路由
│   │   ├── __init__.py
│   │   ├── stt.py
│   │   ├── llm.py
│   │   ├── tts.py
│   │   ├── scorer.py
│   │   └── voice_clone.py
│   ├── core/                        # 核心逻辑
│   │   ├── pipeline.py              # 对话流水线编排
│   │   ├── session_manager.py       # 会话管理
│   │   └── audio_processor.py       # 音频处理工具
│   ├── models/                      # 数据模型
│   │   ├── schemas.py
│   │   └── database.py
│   ├── server.py                    # FastAPI 主入口
│   ├── requirements.txt
│   └── config.yaml                  # 模型路径/参数配置
│
├── docs/                            # 文档
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── PROTOCOL.md                  # 手机-电脑通信协议
│
├── scripts/
│   ├── download_models.sh           # 模型下载
│   └── setup_dev.sh                 # 开发环境初始化
│
├── tests/
│   ├── engine/                      # AI 引擎测试
│   └── mobile/                      # Flutter 端到端测试
│
├── .github/
│   └── workflows/
│       └── ci.yml                   # CI 流水线
│
├── .gitignore
└── README.md
```

## 3. 通信协议设计

### 手机 ↔ 电脑 通信协议 (Protocol)

**传输层**: WebSocket (ws://{desktop_ip}:9876/ws/mobile)

**连接建立流程:**
```
1. [手机] mDNS 搜索 "_voxlingua._tcp" 服务
2. [电脑] 响应 mDNS，返回 IP + 端口 (9876)
3. [手机] 发起 WebSocket 连接
4. [电脑] 验证连接，返回 session_id
5. [手机] 进入就绪状态
```

**消息格式 (JSON):**
```json
// 手机 → 电脑: 发送录音
{
  "type": "audio_input",
  "session_id": "abc123",
  "format": "opus",        // Opus 编码压缩
  "data": "<base64_audio>"
}

// 电脑 → 手机: 回复合成音频
{
  "type": "audio_output",
  "session_id": "abc123",
  "format": "pcm_f32le",
  "sample_rate": 24000,
  "data": "<base64_audio>",
  "text": "Nice to meet you too! How can I help you today?",
  "metadata": {
    "language": "en",
    "emotion": "friendly"
  }
}

// 电脑 → 手机: 发音评分结果
{
  "type": "scoring_result",
  "overall_score": 85.5,
  "dimensions": {
    "phoneme_accuracy": 88.0,
    "fluency": 82.0,
    "prosody": 85.0,
    "completeness": 90.0,
    "grammar": 87.0
  },
  "details": {
    "errors": [
      {"phoneme": "θ", "expected": "θ", "actual": "s", "position": 1},
      {"phoneme": "r", "expected": "ɹ", "actual": "r", "position": 4}
    ]
  }
}
```

## 4. 模型管理

### 显存优化策略

由于目标 GPU 显存为 6-8GB，采用以下优化：

1. **按需加载 (Lazy Loading)**: 只有当前使用的模块才加载到显存
2. **模型卸载 (Model Offloading)**: 切换功能时卸载前一模块
3. **量化推理**: LLM 使用 GGUF Q4_K_M，Whisper 使用 ONNX 量化，CosyVoice 使用 FP16
4. **模型调度器**: 统一管理模型生命周期，避免 OOM

### 模型下载管理

```
engine/
└── models/                         # 自动下载到这里
    ├── whisper/                    # 语音识别模型
    │   └── small.pt
    ├── cosyvoice/                  # 语音合成+声纹克隆
    │   └── CosyVoice-300M/
    ├── llm/                        # 大语言模型
    │   └── qwen2.5-7b-Q4_K_M.gguf
    └── voice_profiles/             # 用户保存的声纹模板
        └── user_profiles/
```

## 5. 安全和隐私

- **纯本地运行**：所有音频数据仅在局域网传输，不经过互联网
- **音频不持久化**：默认不保存用户录音（可配置）
- **声纹模板本地存储**：上传的参考音频仅保存在用户电脑上
