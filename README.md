# VoxLingua 🎤🌍

> **Vox（声音）+ Lingua（语言）** — AI 语音口语对练，专注纠正你的发音

**让任何人声，成为你的多语言口语教练。** 目前主攻 **英语 + 纽约口音**。

---

## 快速启动

### 方案 A：Docker（推荐，无需安装 Python）

```bash
# 1. 启动 AI 引擎
docker compose up -d

# 2. 启动桌面应用（另一个终端）
cd desktop && npm install && npm run dev

# 3. 浏览器打开 http://localhost:5173
```

### 方案 B：本地安装

```bash
# Windows
scripts\setup.bat

# macOS / Linux
chmod +x scripts/setup.sh && ./scripts/setup.sh

# 下载 AI 模型（需要一会，约 8GB）
python scripts/download_models.py --all

# 启动引擎
cd engine && python server.py

# 新终端，启动桌面
cd desktop && npm run dev
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│  💻 Desktop (Vite + React)        📱 Mobile (Flutter)   │
│  ┌─────────────────┐             ┌─────────────────┐    │
│  │  Chat Panel      │             │  Chat Screen     │    │
│  │  Audio Recording │             │  Audio Recording │    │
│  │  Settings Panel  │◄──── WS ───►│  Settings Sheet  │    │
│  │  Correction View│             │  Correction View │    │
│  └─────────────────┘             └─────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket (ws://host:9876/ws/mobile)
┌──────────────────────▼──────────────────────────────────┐
│  ⚙️ AI Engine (Python + FastAPI)                        │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────────────┐       │
│  │ Whisper │  │ CosyVoice│  │  Correction      │       │
│  │  STT    │  │ 3 TTS    │  │  Engine          │       │
│  │ +Phoneme│  │ +Voice   │  │  +Phoneme Align  │       │
│  │ +Prosody│  │ Clone    │  │  +Multi-dim Score│       │
│  └────┬────┘  └────┬─────┘  └────────┬─────────┘       │
│       │            │                 │                  │
│       └────────────┼─────────────────┘                  │
│                    ▼                                     │
│              ┌──────────┐                                │
│              │  LLM     │  (GPT-4o / Claude 云端)        │
│              └──────────┘                                │
└──────────────────────────────────────────────────────────┘
```

---

## 核心技术栈

| 组件 | 技术 | 状态 |
|------|------|------|
| 🖥️ 桌面应用 | Vite + React + TypeScript | ✅ 完成 |
| 📱 手机应用 | Flutter + Material You | ✅ 完成 |
| ⚙️ AI 引擎 | Python + FastAPI + WebSocket | ✅ 完成 |
| 🎙️ STT | **Whisper** (large-v3) + Wav2Vec2 音素对齐 + 韵律分析 | ✅ 代码就绪* |
| 🗣️ TTS | **CosyVoice 3** 流式合成 + 零样本声纹克隆 | ✅ 代码就绪* |
| 🧠 LLM | 云端 API (GPT-4o / Claude) | ✅ 完成 |
| ⭐ 纠错 | 音素级对齐 + ESL 错误模式 + 多维评分 | ✅ 完成 |
| 🐳 容器化 | Docker Compose 一键启动 | ✅ 完成 |

*\* 需要下载模型权重，见下方说明*

---

## 功能特性

### 🎯 发音纠正（核心功能）
- **音素级**纠正 — 显示具体哪个音标发错了（如 `θ → s`）
- **多维评分** — 音素准确度 / 流利度 / 语调 / 完整度
- **三级纠正** — mild（对话中自然纠正）/ medium（显示纠错）/ severe（打断重读）
- **ESL 错误模式库** — 16 种常见中文发音错误，含详细反馈语

### 🗣️ 智能对话
- **场景切换** — Daily Chat / Restaurant / Travel / Job Interview
- **纽约口音** — 上传参考音频即可克隆口音
- **流式 TTS** — 边合成边播放，零等待

### 📱 双终端
- **电脑端** — 浏览器直接使用，支持录音/播放/设置
- **手机端** — Flutter 原生应用，WiFi WebSocket 连接
- **共享上下文** — 两端共用同一个对话历史

---

## 配置说明

所有设置都可以在应用界面中修改：

| 设置 | 说明 | 默认值 |
|------|------|--------|
| Engine URL | AI 引擎 WebSocket 地址 | `ws://localhost:9876/ws/mobile` |
| LLM API Key | OpenAI / 兼容 API 密钥 | 环境变量 `LLM_API_KEY` |
| Conversation Scene | 对话场景 | Daily Chat |
| Voice Profile | 声音配置 | New York Accent |
| Correction Mode | 纠正模式 (Off/Mild/Medium/All) | Medium |
| Interrupt on Severe | 严重错误时打断对话 | On |

---

## 项目结构

```
voxlingua/
├── engine/                    # AI 引擎 (Python + FastAPI)
│   ├── server.py              # FastAPI 服务入口 + WebSocket
│   ├── config.yaml            # 引擎配置
│   ├── requirements.txt       # Python 依赖
│   ├── Dockerfile             # 容器构建
│   ├── api/                   # REST API 路由
│   │   ├── stt.py             #   STT (Whisper)
│   │   ├── tts.py             #   TTS (CosyVoice)
│   │   ├── chat.py            #   LLM 对话
│   │   ├── correction.py      #   发音纠正
│   │   └── scorer.py          #   评分
│   ├── core/                  # 核心逻辑
│   │   ├── pipeline.py        #   对话管线 (STT→LLM→TTS→纠错)
│   │   ├── correction_engine.py  # 纠错引擎 (音素对齐/比较/评分)
│   │   ├── session_manager.py #   会话管理
│   │   └── audio_processor.py #   音频编解码
│   ├── stt/                   # 语音识别
│   │   └── whisper_stt.py     #   Whisper + Wav2Vec2 + 韵律
│   ├── tts/                   # 语音合成
│   │   └── cosyvoice_tts.py   #   CosyVoice 3 + 声纹克隆
│   ├── llm/                   # 大语言模型
│   │   └── cloud.py           #   OpenAI / Claude 客户端
│   └── models/                # 数据模型
│       ├── schemas.py         #   Pydantic 类型定义
│       └── model_manager.py   #   模型生命周期管理
├── desktop/                   # 桌面应用 (Vite + React)
│   ├── src/
│   │   ├── App.tsx            #   主应用
│   │   ├── App.css            #   全局样式 (暗色主题)
│   │   ├── components/        #   UI 组件
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── AudioControls.tsx
│   │   │   └── SettingsPanel.tsx
│   │   └── hooks/             #   React Hooks
│   │       ├── useAudioRecorder.ts
│   │       └── useWebSocket.ts
│   └── package.json
├── mobile/                    # 手机应用 (Flutter)
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   ├── services/
│   │   ├── widgets/
│   │   └── models/
│   └── pubspec.yaml
├── scripts/                   # 工具脚本
│   ├── setup.bat              #   Windows 环境配置
│   ├── setup.sh               #   Unix 环境配置
│   ├── download_models.py     #   模型下载
│   └── dev.bat                #   本地开发启动
└── docker-compose.yml         # 容器编排
```

---

## 模型下载

应用依赖以下预训练模型（首次运行需下载，约 8-12GB）：

```bash
# 自动下载所有模型
python scripts/download_models.py --all

# 或分别下载
python scripts/download_models.py --stt large     # Whisper (~6.5GB)
python scripts/download_models.py --aligner large  # Wav2Vec2 (~4.7GB)

# CosyVoice 需手动下载（约 3.9GB）:
# 见 scripts/download_models.py --tts 的输出指引
```

模型缓存位置：`engine/models/weights/`

---

## 开发

```bash
# 引擎热重载
cd engine && python server.py

# 桌面热重载（另一个终端）
cd desktop && npm run dev

# 浏览器打开 http://localhost:5173
# 引擎 WebSocket 在 ws://localhost:9876/ws/mobile
```

### 代码检查

```bash
# Python lint
cd engine && ruff check . && mypy .

# TypeScript 检查
cd desktop && npx tsc --noEmit

# 构建
cd desktop && npx vite build
```

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。
