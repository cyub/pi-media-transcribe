<p align="center">
  <img src="assets/logo.svg" width="72" height="72" alt="pi-media-transcribe logo">
</p>

<h1 align="center">pi-media-transcribe</h1>

<p align="center">
  <strong>English</strong> ·
  <a href="README.zh-CN.md">简体中文</a> ·
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

<p align="center">Video or audio in, a structured Markdown note out — transcribed locally, filed in your notes folder.</p>

A [Pi](https://pi.dev) skill package that turns a YouTube video, podcast, webinar, meeting recording or any
local media file into a note you would actually keep. Transcription runs **fully offline** on your own
hardware (Whisper, Qwen3-ASR, Parakeet, SenseVoice via
[`handy-transcribe`](https://github.com/cyub/handy-transcribe)) — no audio upload, no per-minute bill.
An LLM then proofreads the transcript, splits it into sections and writes the summary, but only if you
want it: `--raw` skips the model entirely.

- **Local-first:** audio never leaves the machine; the default model runs on CPU and needs no API key.
- **Three separable modes:** transcript only, verbatim note, or polished note — pick per job.
- **Any notes folder:** Obsidian vaults, plain Markdown folders, anything. Frontmatter included.
- **Nine heading languages:** English, 中文, 日本語, 한국어, Русский, Deutsch, Español, Français, Português, detected from the transcript's script.
- **Transcription model:** `model`/`quant` pin the ASR model. `transcribe.sh` injects them when you
  do not pass `--model`, so a machine keeps one stable default instead of guessing per run. The first
  run downloads it (`Qwen3-ASR-0.6B` Q8_0 ≈ 850 MB); `scripts/doctor.sh` shows what would be used and
  whether it is already cached.
- **Long recordings:** one request for a normal talk, chunk-and-merge for a three-hour podcast.
- **Never loses work:** if the LLM step fails, the raw transcript is still written as a note.
- **Bring your own model:** OpenAI, OpenRouter, DeepSeek, or a local Ollama / LM Studio server.

## Demo

```console
$ scripts/to-obsidian.sh "https://www.youtube.com/watch?v=Uz7K757psEU"
==> transcribing
==> correcting, segmenting, summarizing, filing
LLM: deepseek-chat via https://api.deepseek.com (note language: zh, 12 folders offered)
saved: 资料/02-人工智能/AI智能体/高阶Graph RAG：从向量检索困境到图谱增强推理.md
```

A 16-minute Mandarin tech talk becomes an 18.8 KB note — abstract plus 17 sections — with the
transcription itself taking 49 s on an Apple M1 Pro (≈20× realtime, `Qwen3-ASR-0.6B`).

## Install

```bash
pi install npm:pi-media-transcribe
pi install ./pi-media-transcribe    # or from a local checkout
```

Requirements:

```bash
cargo install handy-transcribe     # the offline ASR engine (or: cargo binstall handy-transcribe)
brew install yt-dlp ffmpeg         # only needed for URL input
# python3 3.9+ is used for the note stage
```

Check your setup — the doctor prints exactly what is missing and how to fix it:

```bash
skills/media-transcribe/scripts/doctor.sh
```

## Use it

Ask Pi:

> "Transcribe this video and save it to my notes: https://www.youtube.com/watch?v=..."

Or drive the scripts directly:

```bash
# transcript only — cached, so repeat runs are instant
scripts/transcribe.sh "https://www.youtube.com/watch?v=..."
scripts/transcribe.sh ./meeting.m4a -o meeting.txt

# transcript + polished note (LLM)
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./recording.m4a --vault ~/Documents/Obsidian\ Vault --base Resources
scripts/to-obsidian.sh ./talk.wav --model Qwen3-ASR-1.7B -l zh

# transcript + verbatim note, no LLM at all (offline, free)
scripts/to-obsidian.sh ./lecture.mp4 --raw
scripts/to-obsidian.sh ./meeting.m4a --raw --vault ~/notes/inbox
```

Pass-through options for `handy-transcribe`: `-m/--model`, `-q/--quant`, `-l/--language`,
`--translate`, `--device`, `--no-chunk`, `--keep-fillers`, `--custom-words`, `--json`, `-o`.
Note-level flags: `--raw`, `--vault`, `--base`, `--locale`, `--overwrite`.

> If the scripts arrive without the executable bit (some package managers drop it), either
> `chmod +x scripts/*.sh` or invoke them as `bash scripts/transcribe.sh …`.

## Configuration

Optional. Copy [`config.example.json`](config.example.json) to
`~/.config/pi-media-transcribe/config.json`:

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "baseSubdir": "Resources",
  "locale": "auto",
  "tags": ["auto-transcribed"],
  "model": "Qwen3-ASR-0.6B",
  "quant": "Q8_0",
  "llm": {
    "baseUrl": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "apiKeyEnv": "DEEPSEEK_API_KEY",
    "maxDirectChars": 48000,
    "chunkChars": 24000
  },
  "frontmatter": { "createdField": "created_at", "modifiedField": "last_modify_at" },
  "headings": { "source": "Source", "summary": "Core ideas", "body": "Transcript" }
}
```

- **Notes folder:** `--vault` → `$OBSIDIAN_VAULT` → config → the vault Obsidian itself has open →
  `~/Documents/Obsidian Vault`. Any directory works; Obsidian is just the default.
- **Language:** the body always follows the transcript. Headings are localized for `en`, `zh`, `ja`,
  `ko`, `ru`, `de`, `es`, `fr`, `pt` and detected from the script (kana → Japanese, hangul → Korean,
  CJK → Chinese, Cyrillic → Russian). Other scripts keep English labels; override with `headings`.
- **Other LLMs:** anything OpenAI-compatible.

```json
"llm": { "provider": "openai", "model": "gpt-5-mini" }
"llm": { "provider": "openrouter", "model": "anthropic/claude-sonnet-5" }
"llm": { "baseUrl": "http://localhost:11434/v1", "model": "qwen3:8b" }
```

`llm.provider` picks the endpoint (`deepseek`, `openai`, `openrouter`) together with the matching
`$PROVIDER_API_KEY` variable. **Keys are provider-bound:** a key you gave Pi is only used when the
endpoint belongs to the same provider, so an OpenAI or OpenRouter credential is never posted to
DeepSeek (or vice versa) — if nothing matches, the run stops and tells you why instead of reusing a
foreign credential. A local server (Ollama, LM Studio, vLLM) keeps transcription *and* polishing on
the machine and needs no key at all.

- **Long recordings:** under `llm.maxDirectChars` (default 48 000 chars) one request; beyond that,
  `llm.chunkChars` chunks (default 24 000) are compressed and merged.
- **Safety:** the LLM may only choose from the offered folders, the final path is validated against
  the notes root, and existing notes are never overwritten (a numeric suffix is added; `--overwrite`
  forces it).

## What you get

```markdown
---
created_at: 2026/10/31 22:14
last_modify_at: 2026/10/31 22:14
tags:
  - youtube
  - auto-transcribed
  - RAG
  - knowledge-graph
---
Source: https://www.youtube.com/watch?v=...

## Core ideas
<150–300 word abstract>

---

## Transcript
### Why vector search hits a ceiling
<proofread, segmented body>
```

## How it works

```
URL ──yt-dlp──▶ audio ──▶ handy-transcribe (symphonia → Silero VAD → transcribe.cpp)
                                    │
                              transcript (cached)
                                    │
              LLM (optional): proofread → segment → summarize → pick folder/tags
                                    │
                            Markdown note (frontmatter + summary + body)
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `yt-dlp` fails or times out | Configure a proxy (`export https_proxy=http://127.0.0.1:7890`), or pass a local file |
| Model download stalls | Models come from Hugging Face; point `HF_ENDPOINT` at a mirror or internal proxy, e.g. `https://your-hub-mirror.example` (SHA-256 still verified) |
| `handy-transcribe not found` | `scripts/doctor.sh`, or point `HANDY_TRANSCRIBE_BIN` at the binary |
| HTTP 401/402 from the LLM | Wrong/missing key or no credit — check `llm.apiKeyEnv`, or use `--raw` |
| HTTP 413 / context overflow | Lower `llm.maxDirectChars` and `llm.chunkChars` |
| Note landed at the folder root | No candidate folders: set `baseSubdir` or create one |
| LLM failed but you got a note | That's the built-in fallback (raw transcript). Rerun to retry polishing |

## Limits

- Audio only — no slides, on-screen text, or frame understanding.
- The polished mode costs tokens: one request for a normal recording, one per chunk plus a merge for
  very long ones. `--raw` costs nothing and stays offline.
- `--raw` notes are the transcript verbatim, ASR mistakes included.
- bash + Python 3.9+ on macOS/Linux; on Windows use WSL or Git Bash.

## License

MIT — see [LICENSE](LICENSE). Built on [Handy](https://github.com/cjpais/Handy) and
[transcribe.cpp](https://github.com/handy-computer/transcribe.cpp); the ASR CLI it drives is
[handy-transcribe](https://github.com/cyub/handy-transcribe).
