# pi-media-transcribe

**视频/音频进去，结构化的 Markdown 笔记出来——Obsidian 可直接用，但任意笔记目录都行。**
转写全程本地离线（不按分钟付费），润色要不要用 LLM 由你决定。

一个 [Pi](https://pi.dev) 技能包，三种模式各自独立可用：

| 模式 | 做什么 | 需要 API key？ |
|---|---|---|
| **只转写** | URL 或文件 → 转写文本（带缓存） | 不需要 |
| **落笔记（`--raw`）** | 转写文本 → Markdown 笔记，逐字保留 | **不需要** |
| **落笔记（默认，润色）** | 转写 → LLM 校对/分段/摘要/选目录选标签 → 笔记 | 需要 |

- **转写**：YouTube 视频、播客、网络研讨会、会议录音，或任何本地音视频文件，用本地离线 ASR
  （Whisper / Qwen3-ASR / Parakeet / SenseVoice，底层是
  [`handy-transcribe`](https://github.com/cyub/handy-transcribe)）。音频不上传，没有云端费用。
- **整理成笔记**：润色模式会校对 ASR 错字、按主题分成 `###` 小节、写 150–300 字摘要、在笔记树里
  挑目录、挑 1–3 个主题标签，输出带 frontmatter 的 Markdown 笔记。长录音会分块压缩再合并，
  三小时的播客也不会撑爆上下文。
- **不丢工作**：LLM 步骤失败时，原始转写仍会落成一份笔记。

## 安装

```bash
pi install npm:pi-media-transcribe
```

依赖：

```bash
cargo install handy-transcribe     # 离线 ASR 引擎（或 cargo binstall handy-transcribe）
brew install yt-dlp ffmpeg         # 仅在输入是 URL 时需要
# python3 3.9+ 用于整理笔记阶段
```

装完先体检，它会告诉你缺什么、怎么装：

```bash
skills/media-transcribe/scripts/doctor.sh
```

## 用法

直接跟 Pi 说：

> "把这个视频转录一下存到我的笔记里：https://www.youtube.com/watch?v=..."

或者自己调脚本：

```bash
# 只要转写文本（有缓存，重复跑是秒回）
scripts/transcribe.sh "https://www.youtube.com/watch?v=..."
scripts/transcribe.sh ./会议.m4a -o meeting.txt

# 转写 + 存档成笔记（LLM 润色）
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./录音.m4a --vault ~/Documents/Obsidian\ Vault --base 资料
scripts/to-obsidian.sh ./讲座.wav --model Qwen3-ASR-1.7B -l zh

# 转写 + 存档成笔记，完全不用 LLM（离线、免费、逐字保留）
scripts/to-obsidian.sh ./课程.mp4 --raw
scripts/to-obsidian.sh ./会议.m4a --raw --vault ~/notes/inbox
```

## 配置

可选。把 [`config.example.json`](config.example.json) 复制到
`~/.config/pi-media-transcribe/config.json` 再改：

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "baseSubdir": "资料",
  "locale": "auto",
  "tags": ["自动转录"],
  "llm": {
    "baseUrl": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "apiKeyEnv": "DEEPSEEK_API_KEY",
    "maxDirectChars": 48000,
    "chunkChars": 24000
  },
  "frontmatter": { "createdField": "created_at", "modifiedField": "last_modify_at" },
  "headings": { "source": "来源", "summary": "核心内容", "body": "正文" }
}
```

- **笔记目录探测顺序**：`--vault` → `$OBSIDIAN_VAULT` → 配置文件 → Obsidian 当前打开的 vault
  （读 `obsidian.json`）→ `~/Documents/Obsidian Vault`。**任意目录都行**，Obsidian 只是默认值。
- **笔记语言**跟随转录文本（`locale: "auto"`），连小节标题一起；可钉死 `en`/`zh`。
- **LLM**：任何 OpenAI 兼容端点。没配 key 时自动回落到 Pi 已存的 `~/.pi/agent/auth.json`。
  只有润色模式需要它，`--raw` 完全不调用模型。
- **长录音**：少于 `llm.maxDirectChars`（默认 48000 字符）一次性发给模型；更长则按
  `llm.chunkChars`（默认 24000）分块压缩再合并。

### 多语言支持

笔记正文始终跟随转录文本的语言。三个小节标题内置了 `en`/`zh`/`ja`/`ko`/`ru`/`de`/`es`/`fr`/`pt`
九种语言，可以用 `--locale` 指定，也可以由脚本根据文字系统自动判断（假名→日语、谚文→韩语、
汉字→中文、西里尔→俄语……）。其他文字系统（阿拉伯、希伯来、希腊、泰、天城体）以及英语以外的
拉丁语系语言，标题保持英文、正文仍是原文语言；想要自己的措辞，用配置里的 `headings` 覆盖。

### 换用别的 LLM

任何 OpenAI 兼容端点都行——云端或本地：

```json
"llm": { "baseUrl": "https://api.openai.com", "model": "gpt-5-mini", "apiKeyEnv": "OPENAI_API_KEY" }
"llm": { "baseUrl": "https://openrouter.ai/api", "model": "anthropic/claude-sonnet-5", "apiKeyEnv": "OPENROUTER_API_KEY" }
"llm": { "baseUrl": "http://localhost:11434/v1", "model": "qwen3:8b", "apiKeyEnv": "OLLAMA_API_KEY" }
"llm": { "baseUrl": "http://localhost:1234/v1", "model": "local-model", "apiKeyEnv": "LMSTUDIO_API_KEY" }
```

本地服务（Ollama / LM Studio / vLLM）能让整条链路都不出本机——转写和润色都是。Ollama 不校验 key，
随便给个非空值即可。
- **安全**：LLM 只能从给定的目录列表里选，最终路径会校验在 vault 之内；同名笔记不会被覆盖，
  自动加序号（`--overwrite` 才覆盖）。

## 产物长这样

```markdown
---
created_at: 2026/10/31 22:14
last_modify_at: 2026/10/31 22:14
tags:
  - youtube
  - 自动转录
  - RAG
  - 知识图谱
---
来源：https://www.youtube.com/watch?v=Uz7K757psEU

## 核心内容
<150–300 字摘要>

---

## 正文
### 传统向量检索的底层天花板
<校对并分段后的正文>
```

实测：一段 16 分钟中文技术演讲 → 18.8 KB 笔记（摘要 + 17 个小节），转写本身在 Apple M1 Pro 上
用 `Qwen3-ASR-0.6B` 耗时 49 秒（约 20 倍实时）。

## 工作原理

```
URL ──yt-dlp──▶ 音频 ──▶ handy-transcribe（symphonia → Silero VAD → transcribe.cpp）
                                  │
                            转写文本（带缓存）
                                  │
                        LLM：纠错 → 分段 → 摘要 → 选目录/标签
                                  │
                        Obsidian 笔记（frontmatter + 摘要 + 正文）
```

## 常见问题

| 现象 | 处理 |
|---|---|
| `yt-dlp` 超时/失败 | 配代理（`export https_proxy=http://127.0.0.1:7890`），或自己下好音频传本地文件 |
| 模型下载卡住 | 模型来自 Hugging Face，设 `HF_ENDPOINT=https://hf-mirror.com`（仍做 SHA-256 校验） |
| `handy-transcribe not found` | 跑 `scripts/doctor.sh`，或用 `HANDY_TRANSCRIBE_BIN` 指定路径 |
| LLM 返回 401/402 | key 错或余额不足，检查 `llm.apiKeyEnv`，或直接用 `--raw` |
| 返回 413 / 上下文超限 | 调小配置里的 `llm.maxDirectChars` 和 `llm.chunkChars` |
| 笔记落在根目录 | 没有可选目录：设置 `baseSubdir` 或先建目录 |
| LLM 失败了但拿到了笔记 | 这是内置兜底：保存的是原始转写。重跑同一条命令即可重试润色（转写有缓存） |

## 限制

- 只处理音轨，不看画面（无字幕识别、无幻灯片/关键帧理解）。
- 润色模式消耗 token（普通录音 1 次请求，超长录音每块 1 次 + 合并 1 次）；`--raw` 零成本且全程离线。
- `--raw` 笔记是逐字转写，包含 ASR 错字，不做校对。
- **平台**：脚本是 bash + Python。macOS 和 Linux 开箱可用；Windows 需要 WSL 或 Git Bash
  （`handy-transcribe` 本身在 Windows 上未测试）。

## 许可证

MIT。`handy-transcribe` CLI 及其下载的模型各有自己的许可证。

---

English: [README.md](README.md)
