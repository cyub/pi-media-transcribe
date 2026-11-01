<p align="center">
  <img src="assets/logo.svg" width="72" height="72" alt="pi-media-transcribe logo">
</p>

<h1 align="center">pi-media-transcribe</h1>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>简体中文</strong> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <a href="https://github.com/cyub/pi-media-transcribe/stargazers">
    <img src="https://img.shields.io/github/stars/cyub/pi-media-transcribe?style=flat&logo=github" alt="GitHub stars">
  </a>
  <a href="https://www.npmjs.com/package/pi-media-transcribe">
    <img src="https://img.shields.io/npm/v/pi-media-transcribe?style=flat&logo=npm&logoColor=white" alt="npm version">
  </a>
  <a href="https://github.com/cyub/pi-media-transcribe/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/cyub/pi-media-transcribe/ci.yml?style=flat&logo=githubactions&logoColor=white" alt="CI">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/cyub/pi-media-transcribe?style=flat" alt="License">
  </a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-555?style=flat" alt="Platform">
  <img src="https://img.shields.io/badge/ASR-offline%20%C2%B7%20no%20API%20key-0ea5e9?style=flat" alt="Offline ASR">
</p>

<p align="center">视频/音频进去，结构化的 Markdown 笔记出来——本地转写，直接归档到你的笔记目录。</p>

一个 [Pi](https://pi.dev) 技能包，把 YouTube 视频、播客、网络研讨会、会议录音或任意本地音视频文件，变成一篇
你愿意留着的笔记。转写**完全离线**跑在本机（Whisper / Qwen3-ASR / Parakeet / SenseVoice，底层是
[`handy-transcribe`](https://github.com/cyub/handy-transcribe)）——音频不上传，不按分钟付费。之后再让 LLM
校对、分段、写摘要，但这一步是可选的：`--raw` 完全不碰模型。

- **本地优先**：音频不出本机；默认模型跑 CPU，不需要任何 API key。
- **三种模式可拆开用**：只转写、逐字落笔记、润色落笔记——按任务挑。
- **任意笔记目录**：Obsidian vault、普通 Markdown 文件夹都行，自带 frontmatter。
- **九种标题语言**：English、简体中文、日本語、한국어、Русский、Deutsch、Español、Français、Português，按文字系统自动识别。
- **长录音**：普通演讲一次请求，三小时播客分块压缩再合并。
- **不丢工作**：LLM 步骤失败时，原始转写照样落成笔记。
- **自带模型**：OpenAI、OpenRouter、DeepSeek，或本地 Ollama / LM Studio。

## 演示

```console
$ scripts/to-obsidian.sh "https://www.youtube.com/watch?v=Uz7K757psEU"
==> transcribing
==> correcting, segmenting, summarizing, filing
LLM: deepseek-chat via https://api.deepseek.com (note language: zh, 12 folders offered)
saved: 资料/02-人工智能/AI智能体/高阶Graph RAG：从向量检索困境到图谱增强推理.md
```

一段 16 分钟中文技术演讲 → 18.8 KB 笔记（摘要 + 17 个小节）；转写本身在 Apple M1 Pro 上用
`Qwen3-ASR-0.6B` 耗时 49 秒（约 20 倍实时）。

## 安装

```bash
pi install npm:pi-media-transcribe
pi install ./pi-media-transcribe    # 或从本地检出安装
```

依赖：

```bash
cargo install handy-transcribe     # 离线 ASR 引擎（或 cargo binstall handy-transcribe）
brew install yt-dlp ffmpeg         # 仅输入是 URL 时需要
# 整理笔记阶段需要 python3 3.9+
```

先体检，它会告诉你缺什么、怎么装：

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

# 转写 + 润色笔记（LLM）
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./录音.m4a --vault ~/Documents/Obsidian\ Vault --base 资料
scripts/to-obsidian.sh ./讲座.wav --model Qwen3-ASR-1.7B -l zh

# 转写 + 逐字笔记，完全不用 LLM（离线、免费）
scripts/to-obsidian.sh ./课程.mp4 --raw
scripts/to-obsidian.sh ./会议.m4a --raw --vault ~/notes/inbox
```

透传给 `handy-transcribe` 的参数：`-m/--model`、`-q/--quant`、`-l/--language`、`--translate`、
`--device`、`--no-chunk`、`--keep-fillers`、`--custom-words`、`--json`、`-o`。
笔记层参数：`--raw`、`--vault`、`--base`、`--locale`、`--overwrite`。

> 如果脚本丢了可执行位（某些包管理器会），用 `chmod +x scripts/*.sh`，或者用 `bash scripts/transcribe.sh …` 调用。

## 配置

可选。把 [`config.example.json`](config.example.json) 复制到
`~/.config/pi-media-transcribe/config.json`：

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

- **笔记目录**：`--vault` → `$OBSIDIAN_VAULT` → 配置文件 → Obsidian 当前打开的 vault →
  `~/Documents/Obsidian Vault`。任意目录都可以，Obsidian 只是默认值。
- **语言**：正文始终跟随转录文本。小节标题内置 `en`/`zh`/`ja`/`ko`/`ru`/`de`/`es`/`fr`/`pt`，
  并按文字系统自动判断（假名→日语、谚文→韩语、汉字→中文、西里尔→俄语）。其他文字系统保持英文标题，
  可用 `headings` 覆盖。
- **换用别的 LLM**：任何 OpenAI 兼容端点都行。

```json
"llm": { "baseUrl": "https://api.openai.com", "model": "gpt-5-mini", "apiKeyEnv": "OPENAI_API_KEY" }
"llm": { "baseUrl": "https://openrouter.ai/api", "model": "anthropic/claude-sonnet-5", "apiKeyEnv": "OPENROUTER_API_KEY" }
"llm": { "baseUrl": "http://localhost:11434/v1", "model": "qwen3:8b", "apiKeyEnv": "OLLAMA_API_KEY" }
```

本地服务（Ollama / LM Studio / vLLM）能让转写和润色都不出本机；Ollama 不校验 key，随便给个非空值即可。

- **长录音**：少于 `llm.maxDirectChars`（默认 48000 字符）一次性发给模型；更长则按 `llm.chunkChars`
  （默认 24000）分块压缩再合并。
- **安全**：LLM 只能从给定目录列表里选，最终路径校验在笔记目录内；同名笔记不会被覆盖（自动加序号，
  `--overwrite` 才覆盖）。

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

## 工作原理

```
URL ──yt-dlp──▶ 音频 ──▶ handy-transcribe（symphonia → Silero VAD → transcribe.cpp）
                                  │
                            转写文本（带缓存）
                                  │
              LLM（可选）：纠错 → 分段 → 摘要 → 选目录/标签
                                  │
                        Markdown 笔记（frontmatter + 摘要 + 正文）
```

## 常见问题

| 现象 | 处理 |
|---|---|
| `yt-dlp` 超时/失败 | 配代理（`export https_proxy=http://127.0.0.1:7890`），或改传本地文件 |
| 模型下载卡住 | 模型来自 Hugging Face，设 `HF_ENDPOINT=https://hf-mirror.com`（仍做 SHA-256 校验） |
| `handy-transcribe not found` | 跑 `scripts/doctor.sh`，或用 `HANDY_TRANSCRIBE_BIN` 指定路径 |
| LLM 返回 401/402 | key 错或余额不足，检查 `llm.apiKeyEnv`，或直接用 `--raw` |
| 返回 413 / 上下文超限 | 调小 `llm.maxDirectChars` 和 `llm.chunkChars` |
| 笔记落在目录根部 | 没有可选目录：设置 `baseSubdir` 或先建目录 |
| LLM 失败了但拿到了笔记 | 内置兜底保存的是原始转写。重跑同一条命令即可重试润色 |

## 限制

- 只处理音轨，不看画面（无字幕识别、无幻灯片/关键帧理解）。
- 润色模式消耗 token（普通录音 1 次请求，超长录音每块 1 次 + 合并 1 次）；`--raw` 零成本且全程离线。
- `--raw` 笔记是逐字转写，包含 ASR 错字，不做校对。
- macOS / Linux 上是 bash + Python 3.9+；Windows 需要 WSL 或 Git Bash。

## 许可证

MIT，见 [LICENSE](LICENSE)。基于 [Handy](https://github.com/cjpais/Handy) 与
[transcribe.cpp](https://github.com/handy-computer/transcribe.cpp)；它调用的 ASR CLI 是
[handy-transcribe](https://github.com/cyub/handy-transcribe)。
