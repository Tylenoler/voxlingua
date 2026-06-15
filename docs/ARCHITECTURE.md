# VoxLingua 架构设计文档

## 1. 系统架构概览

### 双终端架构（电脑 + 手机，共享同一个 AI 引擎）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  💻 Desktop App (Tauri v2)                                              │
│                                                                         │
│  ╔═══════════════════════════════════════════════════════════════╗      │
│  ║ 🎤 终端 A: 电脑麦克风                                         ║      │
│  ║    录音 → 本地 IPC → AI 引擎 → 电脑扬声器播放                  ║      │
│  ║    延迟最低（无网络传输）                                       ║      │
│  ╚═══════════════════════════════════════════════════════════════╝      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Tauri Main Process (Rust)                                    │       │
│  │  ├── 窗口管理（可最小化到托盘，后台持续运行）                   │       │
│  │  ├── Sidecar 生命周期管理（启动/停止/重启 Python 引擎）        │       │
│  │  └── 本地文件系统 API（声纹模板、对话历史存储）                 │       │
│  └──────────────────┬──────────────────────────────────────────┘       │
│                     │ IPC                                              │
│  ┌──────────────────▼──────────────────────────────────────────┐       │
│  │  Frontend (React + TypeScript)                               │       │
│  │  ├── 🎤 录音按钮（直接使用电脑麦克风）                        │       │
│  │  ├── 对话面板 + 实时纠正显示                                  │       │
│  │  ├── 声纹管理：上传/切换/预设纽约口音模板                     │       │
│  │  ├── LLM 配置：API Key 设置                                   │       │
│  │  └── 纠正参数：灵敏度/开关控制                                │       │
│  └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Python Sidecar — AI Engine Server (FastAPI)                 │       │
│  │  ───────────────────────────────────────                     │       │
│  │  [Uvicorn on localhost:9876]                                 │       │
│  │                                                                     │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────────┐     │
│  │  │  STT     │  │ 流式 TTS   │  │  评分引擎  │  │ LLM 客户端   │     │
│  │  │ Whisper  │  │ CosyVoice  │  │  音素对齐  │  │ └── 云端API  │     │
│  │  │ 本地     │  │ 流式输出   │  │  特征对比  │  │  (GPT/Claude)│     │
│  │  └──────────┘  └────────────┘  └────────────┘  └──────────────┘     │
│  │                                                                     │
│  │  ┌──────────────────────────────────────────────────────────────┐  │
│  │  │  Voice Profile Store (纽约口音 ≈ 用户自定义)                   │  │
│  │  └──────────────────────────────────────────────────────────────┘  │
│  │                                                                     │
│  │  ┌──────────────────────────────────────────────────────────┐     │
│  │  │  LAN WebSocket Server (端口 9876)                          │     │
│  │  │  /ws/mobile — 手机端主通道                                 │     │
│  │  │  /ws/correction — 实时纠正流                              │     │
│  │  └──────────────────────────────────────────────────────────┘     │
│  └─────────────────────────────────────────────────────────────┘     │
└──────────────────────────┬────────────────────────────────────────────┘
                           │ 局域网 WiFi (WebSocket)
┌──────────────────────────▼────────────────────────────────────────────┐
│  📱 Mobile App (Flutter) — 简约 UI                                    │
│                                                                       │
│  ╔═══════════════════════════════════════════════════════════════╗    │
│  ║ 🎤 终端 B: 手机麦克风                                         ║    │
│  ║    录音 → WiFi WebSocket → AI引擎 → 手机扬声器播放             ║    │
│  ║    便携（躺着/走动都能用）                                     ║    │
│  ╚═══════════════════════════════════════════════════════════════╝    │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  Auto Discovery (mDNS) → "VoxLingua Desktop found!"       │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  对话界面 (简约气泡)  ← 实时纠正反馈                           │    │
│  │  发音评分卡片 ← 错误音素高亮                                  │    │
│  │  [             🎤 按住说话          ]                         │    │
│  └──────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘
```

> **双终端场景**：你坐在电脑前就用电脑麦克风直接说（无网络延迟），离开座位拿起手机继续说（WiFi 传输）。共享同一个对话上下文，AI 记忆不中断。

## 2. 目录结构

```
voxlingua/
├── desktop/                         # Tauri 桌面应用
│   ├── src-tauri/
│   │   ├── src/
│   │   │   ├── main.rs              # 入口
│   │   │   ├── sidecar.rs           # Python 进程管理
│   │   │   ├── commands.rs          # Tauri IPC 命令
│   │   │   └── discovery.rs         # mDNS 广播
│   │   ├── Cargo.toml
│   │   └── tauri.conf.json
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── tailwind.config.js
│   └── package.json
│
├── mobile/                          # Flutter 手机应用
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app.dart                 # App 配置 + 主题（简约 Material You）
│   │   ├── theme/
│   │   │   └── app_theme.dart       # 极简主题定义
│   │   ├── screens/
│   │   │   ├── chat_screen.dart     # 主对话界面
│   │   │   ├── correction_screen.dart # 纠正详情页
│   │   │   └── settings_screen.dart # 设置
│   │   ├── widgets/
│   │   │   ├── chat_bubble.dart     # 对话气泡
│   │   │   ├── correction_banner.dart # 纠正提示条
│   │   │   ├── score_card.dart      # 评分卡片
│   │   │   └── record_button.dart   # 录音按钮
│   │   ├── services/
│   │   │   ├── websocket_service.dart
│   │   │   ├── discovery_service.dart
│   │   │   └── audio_service.dart
│   │   └── models/
│   │       ├── chat_message.dart
│   │       ├── correction.dart
│   │       └── score.dart
│   └── pubspec.yaml
│
├── engine/                          # Python AI 引擎
│   ├── api/
│   │   ├── __init__.py
│   │   ├── stt.py                   # POST /api/stt
│   │   ├── chat.py                  # POST /api/chat (LLM 路由)
│   │   ├── tts.py                   # POST /api/tts
│   │   ├── scorer.py                # POST /api/score
│   │   └── correction.py            # POST /api/correct (音素纠正)
│   ├── core/
│   │   ├── pipeline.py              # 对话流水线编排
│   │   ├── correction_engine.py     # ⭐ 发音纠正引擎 (核心)
│   │   │   ├── phoneme_aligner.py   #   音素对齐
│   │   │   ├── accent_comparator.py #   口音对比
│   │   │   └── feedback_generator.py # 纠正反馈生成
│   │   ├── session_manager.py
│   │   └── audio_processor.py
│   ├── models/
│   │   ├── schemas.py
│   │   └── database.py
│   ├── llm/                         # LLM 客户端
│   │   └── cloud.py                 # 云端 API (GPT-4o/Claude)
│   ├── voice_profiles/              # 声纹模板目录
│   │   └── new_york/                # 纽约口音模板
│   │       ├── reference.wav        # 你提供的参考音频
│   │       └── profile.json         # 声纹特征文件
│   ├── server.py                    # FastAPI 主入口
│   ├── requirements.txt
│   └── config.yaml
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── PROTOCOL.md
│
├── scripts/
│   ├── download_models.sh
│   └── setup_dev.sh
│
├── tests/
│   ├── engine/
│   ├── desktop/
│   └── mobile/
│
├── .github/workflows/ci.yml
├── .gitignore
└── README.md
```

## 3. 发音纠正引擎设计（核心模块）

这是本项目最具技术深度的部分。

### 架构图

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Input Audio  │───►│  Whisper STT  │───►│  识别文本     │
│  (用户录音)    │    │  + 时间戳     │    │  "I think..." │
└──────────────┘    └──────┬───────┘    └──────▲────────┘
                           │                   │
                           ▼                   │
┌──────────────────────────────────────────────┘
│  Forced Alignment (Wav2Vec2 + CTC)
│  → 音素级时间戳映射
│  → "TH IH NG K" → [θ] [ɪ] [ŋ] [k]
└─────────────────────┬───────────────────────
                      │
                      ▼
┌──────────────────────────────────────────────┐
│  Acoustic Feature Comparison                  │
│  ──────────────────────────                   │
│  用户音素特征 vs 纽约口音参考特征               │
│                                              │
│  MFCC + F0 + Formant 对比                     │
│  → 每个音素的偏离度分数                        │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│  Error Classification (三级)                  │
│  ────────────────────────                    │
│                                              │
│  ██ 轻微 (score ≥ 80)                        │
│  → AI 对话中自然带出正确发音                   │
│  → "I think it's nice" → "Yes, I think       │
│     (emphasized) it's really nice!"          │
│                                              │
│  ██ 中等 (60 ≤ score < 80)                   │
│  → 手机端实时显示文字纠正条                     │
│  → "注意: think 的 th 要咬舌"                │
│                                              │
│  ██ 严重 (score < 60)                        │
│  → 打断对话 (用户可选开关)                     │
│  → 播放正确发音示范                            │
│  → 用户跟读直到通过                            │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│  Feedback Generation                          │
│  → 文本纠正提示 (手机端渲染)                   │
│  → 正确发音音频 (TTS 局部合成)                │
│  → 评分数据 (多维分数)                        │
└──────────────────────────────────────────────┘
```

### 音素对比算法

```
目标音素: [θ] (voiceless dental fricative)
用户发音: [s] (voiceless alveolar fricative)

声学差异:
  - F2 (第2共振峰): 目标 ~1900Hz, 用户 ~1500Hz
  - 频谱斜率差异: ~12dB
  - 持续时间差异: ~30ms

→ 音素偏离度: 72/100 → "中等错误"
→ 纠正建议: "th 音舌尖要放在上下齿之间，不要发成 s"
```

## 4. 通信协议更新

### 新增纠正消息

**电脑 → 手机：实时纠正**
```json
{
  "type": "correction",
  "payload": {
    "level": "medium",           // "mild" | "medium" | "severe"
    "user_text": "I sink it's good",
    "corrected_text": "I think it's good",
    "errors": [
      {
        "word": "think",
        "phoneme": "θ",
        "user_phoneme": "s",
        "position": 0,
        "severity": "medium",
        "feedback": "注意 'think' 的 th 音，舌尖要放在上下齿之间"
      }
    ],
    "audio_correction": "<base64_correct_pronunciation>",
    "overall_score": 72
  }
}
```

### 新增控制消息

**手机 → 电脑：开关纠正模式**
```json
{
  "type": "set_correction_mode",
  "payload": {
    "mode": "medium",           // "off" | "mild_only" | "medium" | "all"
    "interrupt_on_severe": true // 严重错误是否打断对话
  }
}
```

## 5. LLM 客户端

| 模式 | 使用 | 延迟 |
|------|------|------|
| 有网络 + 已配置 API Key | 云端 API (GPT-4o/Claude) | ~1-2s |
| 无 Key / 无网络 | **无法对话**（提示用户配置 Key） | — |

> **为什么纯云端？**
> 现阶段专注把云端 LLM 的对话体验做到最好。日常聊天的自然度是用户体验的关键——GPT-4o 级别的对话能力远超本地 7B 模型，能让用户感觉像在跟真人聊天。未来可以考虑加入本地小模型做离线降级。

> **API Key 配置**：用户在桌面端设置页面填入 Key，引擎启动时加载，手机端无需额外操作。

## 6. 纽约口音声纹模板

你提供一段参考音频后，系统会：
1. 提取声纹特征（CosyVoice speaker embedding）
2. 保存为 `engine/voice_profiles/new_york/`
3. 所有 TTS 输出自动使用该声纹
4. 发音评分时以该口音为标准模板进行对比

**参考音频要求：**
- 时长：3-10 秒
- 内容：自然的英语口语（最好包含多种音素）
- 格式：WAV / MP3
- 无背景噪音
