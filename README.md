# VoxLingua 🎤🌍

> **Vox（声音）+ Lingua（语言）** — AI 语音口语对练，专注纠正你的发音

**让任何人声，成为你的多语言口语教练。** 目前主攻 **英语 + 纽约口音**。

## 这是什么？

**VoxLingua** 是一套**电脑 + 手机双端**的 AI 口语对练系统。

| 💻 电脑端 (Tauri + Python) | 📱 手机端 (Flutter) |
|---------------------------|-------------------|
| 跑所有 AI 模型（本地） | 便携麦克风 + 扬声器 |
| 语音识别 (Whisper) | 录音 → 发送电脑 |
| 语音合成 (CosyVoice 纽约口音) | 接收音频 → 播放 |
| **发音纠正引擎** ⭐ | **实时显示纠正提示** |
| 对话 API (云端/本地 LLM) | 简约对话 UI |

> **为什么这样设计？** 模型跑在电脑 GPU 上，手机只做交互——兼顾便携性和算力，所有数据在局域网传输，隐私安全。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🗣️ **日常口语对练** | 跟 AI 用英语聊日常话题，像跟纽约本地人聊天 |
| 🎯 **发音纠正** | ⭐ 核心功能 — 音素级纠正（th→s 这种都会标出来） |
| 🎤 **纽约口音声纹** | 上传你的参考音频，AI 就用这个口音跟你说话 |
| 📊 **多维评分** | 音素准确度 / 语调 / 流利度 / 完整度 |
| 🧠 **云端 LLM 加持** | 对话更自然（可选本地 LLM 离线回退） |

## 🧰 技术栈

| 组件 | 技术 |
|------|------|
| 🖥️ 桌面应用 | Tauri (Rust) + React + TailwindCSS |
| 📱 手机应用 | Flutter (简约 Material You) |
| ⚙️ AI 引擎 | Python + FastAPI |
| 🎙️ STT | Whisper (本地) |
| 🗣️ TTS + 声纹克隆 | CosyVoice (本地) |
| 🧠 LLM | 云端 API (GPT-4o/Claude) → 降级 → 本地 Qwen GGUF |
| 🔗 连接 | WebSocket + mDNS 自动发现 (WiFi) |
| ⭐ 发音纠正 | 音素对齐 + 声学特征对比 (本地) |

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/Tylenoler/voxlingua.git
cd voxlingua

# 2. 下载 AI 模型
bash scripts/download_models.sh

# 3. 启动 AI 引擎
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
├── desktop/     # Tauri 桌面应用
├── mobile/      # Flutter 手机应用 (简约 UI)
├── engine/      # Python AI 引擎
│   └── core/correction_engine.py  ← ⭐ 核心纠正模块
├── docs/        # 文档
├── scripts/     # 辅助脚本
└── tests/       # 测试
```

## 🔒 隐私

- **纯本地语音处理**: STT/TTS/评分全部在你电脑上跑
- **LLM 可选云端**: 不配置 API Key 时自动使用本地模型
- **音频不保存**: 默认不持久化录音数据

## 📜 许可

MIT License
