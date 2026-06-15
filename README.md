# VoxLingua 🎤🌍

> **Vox（声音）+ Lingua（语言）** — AI 语音口语对练，专注纠正你的发音

**让任何人声，成为你的多语言口语教练。** 目前主攻 **英语 + 纽约口音**。

## 这是什么？

**VoxLingua** 是一套**电脑 + 手机双终端**的 AI 口语对练系统。

| 💻 **终端 A: 电脑** (Tauri + Python) | 📱 **终端 B: 手机** (Flutter) |
|-------------------------------|---------------------------|
| 🎤 直接对电脑麦克风说话 | 🎤 对手机麦克风说话 |
| 🔗 **本地 IPC** → AI 引擎 → 扬声器 | 🔗 **WiFi WebSocket** → AI 引擎 → 扬声器 |
| ⚡ **零网络延迟** | 🚶 **便携，躺着也能用** |
| 语音识别 (Whisper) + **流式**语音合成 (CosyVoice) | 简约对话 UI + 实时纠正显示 |
| **发音纠正引擎** ⭐ + LLM 云端 API | 双端共享同一个对话上下文 |

> **为什么这样设计？** 模型跑在电脑 GPU 上，手机只做交互——兼顾便携性和算力，所有数据在局域网传输，隐私安全。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🗣️ **日常口语对练** | 跟 AI 用英语聊日常话题，像跟纽约本地人聊天 |
| 🎯 **发音纠正** | ⭐ 核心功能 — 音素级纠正（th→s 这种都会标出来） |
| 🎤 **双麦克风终端** | 电脑对讲 / 手机对讲，共享上下文无缝切换 |
| 🗣️ **纽约口音声纹** | 上传你的参考音频，AI 就用这个口音跟你说话 |
| 📊 **多维评分** | 音素准确度 / 语调 / 流利度 / 完整度 |
| 🧠 **云端 LLM 加持** | GPT-4o / Claude 级别的对话自然度 |

## 🧰 技术栈

| 组件 | 技术 |
|------|------|
| 🖥️ 桌面应用 | Tauri (Rust) + React + TailwindCSS |
| 📱 手机应用 | Flutter (简约 Material You) |
| ⚙️ AI 引擎 | Python + FastAPI |
| 🎙️ STT | Whisper (本地) |
| 🗣️ TTS + 声纹克隆 | CosyVoice **流式合成** (本地) |
| 🧠 LLM | 云端 API (GPT-4o/Claude) |
| 🔗 连接 | WebSocket + mDNS 自动发现 (WiFi) |
| ⭐ 发音纠正 | 音素对齐 + 声学特征对比 (本地) |

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/Tylenoler/voxlingua.git
cd voxlingua

# 2. 下载 AI 语音模型
bash scripts/download_models.sh

# 3. 配置 API Key
echo "OPENAI_API_KEY=sk-your-key-here" > engine/.env

# 4. 启动 AI 引擎
cd engine
pip install -r requirements.txt
python server.py            # 启动 :9876

# 4. 启动桌面应用 (新终端)
cd desktop
npm install
npm run tauri dev

# 5. 启动手机应用 (连接电脑 WiFi)
cd mobile
flutter run
```

## 📂 项目结构

```
voxlingua/
├── desktop/     # Tauri 桌面应用 (终端 A: 电脑麦克风)
├── mobile/      # Flutter 手机应用 (终端 B: 手机麦克风)
├── engine/      # Python AI 引擎
│   └── core/correction_engine.py  ← ⭐ 核心纠正模块
├── docs/        # 文档
├── scripts/     # 辅助脚本
└── tests/       # 测试
```

## 🔒 隐私

- **纯本地语音处理**: STT/TTS/评分全部在你电脑上跑
- **LLM 走云端**: 需要配置 API Key（OpenAI / Anthropic 等）
- **音频不保存**: 默认不持久化录音数据

## 📜 许可

MIT License
