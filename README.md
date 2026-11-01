# pi-media-transcribe

**Video or audio in, a structured Markdown note out — Obsidian-ready, but any notes folder works.**
Transcribed locally (no cloud ASR bill), polished by an LLM only if you want it.

A [Pi](https://pi.dev) skill package with three modes, each usable on its own:

| Mode | What happens | Needs an API key? |
|---|---|---|
| **Transcribe** | URL or file → transcript text (cached) | no |
| **Note, raw** (`--raw`) | transcript → Markdown note, verbatim | **no** |
| **Note, polished** (default) | transcript → LLM proofreads, segments, summarises, picks folder + tags → note | yes |

- **Transcribe** any YouTube video, podcast, webinar, meeting recording, or local audio/video file
  with local offline ASR (Whisper, Qwen3-ASR, Parakeet, SenseVoice, … via
  [`handy-transcribe`](https://github.com/cyub/handy-transcribe)). Nothing is uploaded, there is no
  per-minute cost.
- **File it as a note**: the polished mode proofreads ASR output, segments it into `###` sections,
  writes a 150–300 word abstract, picks a folder in your notes tree, picks 1–3 topic tags, and
  writes a frontmatter-ready Markdown note. Long recordings are compressed chunk by chunk and merged,
  so a 3-hour podcast does not blow the model's context window.
- **Never lose a transcript**: if the LLM step fails, the raw transcript is still written as a note.

## Install

```bash
pi install npm:pi-media-transcribe
```

Requirements:

```bash
cargo install handy-transcribe     # the offline ASR engine (or: cargo binstall handy-transcribe)
brew install yt-dlp ffmpeg         # only needed for URL input
# python3 3.9+ is used for the note stage
```

Then check your setup — the doctor prints exactly what is missing and how to fix it:

```bash
skills/media-transcribe/scripts/doctor.sh
```

## Use it

Just ask Pi:

> "Transcribe this video and save it to my notes: https://www.youtube.com/watch?v=..."

Or drive the scripts directly:

```bash
# transcript only — cached, so repeat runs are instant
scripts/transcribe.sh "https://www.youtube.com/watch?v=..."
scripts/transcribe.sh ./meeting.m4a -o meeting.txt

# transcript + note in the vault (LLM polished)
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./recording.m4a --vault ~/Documents/Obsidian\ Vault --base Resources
scripts/to-obsidian.sh ./talk.wav --model Qwen3-ASR-1.7B -l zh

# transcript + note, no LLM at all (offline, free, verbatim)
scripts/to-obsidian.sh ./lecture.mp4 --raw
scripts/to-obsidian.sh ./meeting.m4a --raw --vault ~/notes/inbox
```

## Configuration

Optional. Copy [`config.example.json`](config.example.json) to
`~/.config/pi-media-transcribe/config.json` and edit:

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "baseSubdir": "Resources",
  "locale": "auto",
  "tags": ["auto-transcribed"],
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

- **Notes folder detection**: `--vault` → `$OBSIDIAN_VAULT` → config → the vault Obsidian itself
  has open (read from `obsidian.json`) → `~/Documents/Obsidian Vault`. **Any directory works** —
  Obsidian is just the default; plain Markdown folders behave the same.
- **Note language** follows the transcript (`locale: "auto"`), including the section headings. Pin
  `en` or `zh` to force one.
- **LLM**: any OpenAI-compatible chat endpoint. Without a key it falls back to the DeepSeek key Pi
  already stores in `~/.pi/agent/auth.json`. Only the polished mode needs it — `--raw` never calls a
  model.
- **Long recordings**: transcripts under `llm.maxDirectChars` (default 48 000 chars) go to the model
  in one request; longer ones are compressed in `llm.chunkChars` chunks (default 24 000) and merged.
- **Safety**: the LLM may only choose from the folders it is shown, and the resulting path is
  validated against the vault root. Existing notes are never overwritten — a numeric suffix is
  added instead (`--overwrite` to replace).

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
Source：https://www.youtube.com/watch?v=...

## Core ideas
<150–300 word abstract>

---

## Transcript
### Why vector search hits a ceiling
<proofread, segmented body>
```

Measured: a 16-minute Mandarin tech talk → 18.8 KB note (摘要 + 17 sections), transcription took 49 s
on an Apple M1 Pro with `Qwen3-ASR-0.6B` (≈20× realtime).

## How it works

```
URL ──yt-dlp──▶ audio ──▶ handy-transcribe (symphonia → Silero VAD → transcribe.cpp)
                                    │
                              transcript (cached)
                                    │
                          LLM: proofread → segment → summarize → pick folder/tags
                                    │
                            Obsidian note (frontmatter + summary + body)
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `yt-dlp` fails or times out | Configure a proxy (`export https_proxy=http://127.0.0.1:7890`), or pass a local file instead |
| Model download stalls | Models come from Hugging Face; set `HF_ENDPOINT=https://hf-mirror.com` (SHA-256 still verified) |
| `handy-transcribe not found` | `scripts/doctor.sh`, or point `HANDY_TRANSCRIBE_BIN` at the binary |
| HTTP 401/402 from the LLM | Wrong/missing key or no credit — check `llm.apiKeyEnv`, or use `--raw` |
| HTTP 413 / context overflow | Lower `llm.maxDirectChars` and `llm.chunkChars` in the config |
| Note landed at the notes-folder root | No candidate folders: set `baseSubdir` or create one |
| LLM step failed but you got a note | That is the built-in fallback: it saved the raw transcript. Rerun the same command (transcript is cached) to retry polishing |

## Limits

- Audio only — no slides, on-screen text, or frame understanding.
- The polished mode costs tokens (one request for a normal recording, one per chunk plus one merge
  for very long ones); `--raw` costs nothing and stays offline.
- `--raw` notes are the transcript verbatim, including ASR mistakes — no proofreading.

## License

MIT. The `handy-transcribe` CLI and the models it downloads carry their own licenses.

---

中文文档：[README.zh-CN.md](README.zh-CN.md)
