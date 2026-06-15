# VoxLingua 🎤🌍

> **Vox（声音）+ Lingua（语言）** — 基于本地大模型的 AI 语音口语对练系统

让任何人的声音，成为你的多语言口语教练。

## ✨ 这是什么？

**VoxLingua** 是一套**电脑 + 手机双端**的 AI 语音对练系统。

电脑跑所有 AI 模型，手机作为便携交互终端——你拿着手机，对着麦克风说话，AI 用你选定的人物声纹在对话场景中回应你，并给你的发音实时打分。

### 核心场景

| 场景 | 说明 |
|------|------|
| 🎯 **口语对练** | 模拟餐厅、面试、旅行等真实场景，与 AI 沉浸式对话 |
| 🗣️ **声纹复刻** | 上传一段音频（比如你喜欢的动漫角色/名人声音），AI 就用这个声音跟你聊天 |
| 📖 **单词练习** | 跟读 + 音素级发音评分，帮你纠正每个音节的发音 |
| 📊 **智能评分** | 准确度、流利度、韵律、完整度——全方位量化进步 |
| 🌍 **多语言** | 英语 / 日语 / 韩语 / 中文… 可自由扩展 |

## 🏗️ 架构

```
💻 电脑端 (Tauri + Python)         📱 手机端 (Flutter)
┌────────────────────┐           ┌──────────────────┐
│  AI 引擎服务         │◄──WiFi──►│  录音/播放        │
│  ──────────          │ WebSocket│  对话界面          │
│  • STT 语音识别      │          │  评分展示          │
│  • LLM 对话引擎      │          │  ❌ 不跑模型        │
│  • CosyVoice 语音合成│          └──────────────────┘
│  • 声纹克隆          │
│  • 发音评分          │
│  • 所有模型本地运行    │
└────────────────────┘
```

> **为什么这样设计？**
> 模型跑在电脑上（高性能 GPU），手机做薄客户端——兼顾便携性和算力，且所有数据都在局域网内传输，完全隐私。

## 🧰 技术栈

| 组件 | 技术 |
|------|------|
| 🖥️ 桌面应用 | Tauri (Rust) + React + TailwindCSS |
| 📱 手机应用 | Flutter (Dart) |
| ⚙️ AI 引擎 | Python + FastAPI |
| 🔗 通信 | WebSocket + mDNS 自动发现 |
| 🎙️ STT | Whisper (OpenAI) |
| 🧠 LLM | Qwen2.5-7B (量化 GGUF) |
| 🗣️ TTS + 声纹克隆 | CosyVoice (阿里达摩院) |

## 🚀 快速开始 (开发环境)

```bash
# 1. 克隆仓库
git clone https://github.com/Tylenoler/voxlingua.git
cd voxlingua

# 2. 下载 AI 模型
bash scripts/download_models.sh

# 3. 启动 AI 引擎
cd engine
pip install -r requirements.txt
python server.py

# 4. 启动桌面应用 (新终端)
cd desktop
npm install
npm run tauri dev

# 5. 启动手机应用 (新终端)
cd mobile
flutter run
```

## 📂 项目结构

```
voxlingua/
├── desktop/         # Tauri 桌面应用 (Rust + React)
├── mobile/          # Flutter 手机应用
├── engine/          # Python AI 引擎 (FastAPI)
├── docs/            # 文档 (PRD, 架构, 协议)
├── scripts/         # 辅助脚本
└── tests/           # 测试
```

## 🔒 隐私设计

- **纯本地运行**：所有 AI 推理在本地完成，数据不离开你的局域网
- **音频不持久化**：默认不保存录音，隐私优先
- **声纹模板本地存储**：上传的参考音频仅保存在你电脑上

## 📜 许可

MIT License — 欢迎贡献和 Fork！

---

> 正在开发中 🚧 欢迎一起参与！
