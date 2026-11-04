---
name: media-transcribe
description: "Transcribe, caption, subtitle, or extract the speech from a YouTube video, podcast, webinar, lecture, meeting recording, or any local audio/video file, then clean it into a structured Markdown note. Runs ASR locally (Whisper / Qwen3-ASR / Parakeet / SenseVoice via handy-transcribe, no cloud, no API key for the transcription step). Two ways to file it: let an LLM fix ASR errors, segment the text with headings, write a summary and place it in a notes folder with tags — or use --raw to keep the transcript verbatim with no LLM at all. Works with an Obsidian vault or any Markdown notes folder. 转写/转录/听写/提取字幕/整理成笔记：YouTube、播客、会议录音、视频、本地音视频文件 → 带摘要和小标题的 Markdown 笔记（或 --raw 逐字保留，不需要任何 API key）。"
---

# Media transcription → Markdown note

Turn a video/audio source into text, then into a note you would actually keep.

| Mode | Script | Output | API key |
|---|---|---|---|
| Transcribe only | `scripts/transcribe.sh` | plain text/JSON transcript (cached) | no |
| Note, verbatim | `scripts/to-obsidian.sh --raw` | note with the transcript exactly as transcribed | no |
| Note, polished | `scripts/to-obsidian.sh` | proofread, sectioned, summarised note with tags | yes |
| Environment check | `scripts/doctor.sh` | what is ready, what to install | — |

Default to the polished mode when the user wants a readable note or a summary. Use `--raw` when there is
no LLM key, the user wants zero cost / full offline, or the content is sensitive and must not leave the
machine.

## When to use it

- The user asks to transcribe / 转录 / 转写 / 提取字幕 / 听写 a URL or a media file.
- The user wants the *content* of a video or podcast as text they can read or search.
- The user wants a video/podcast/meeting turned into a note, summary, or knowledge-base entry.

Do **not** use it for: reading a web page (use `web_fetch`), summarising a document you already
have as text (just read it), or describing video *frames* (this tool only handles the audio track).

## Requirements

```bash
scripts/doctor.sh          # prints exactly what is missing and how to install it
```

- `handy-transcribe` — the offline ASR CLI (Rust). Install with `cargo install handy-transcribe`,
  `cargo binstall handy-transcribe`, or a prebuilt binary from
  <https://github.com/cyub/handy-transcribe/releases>. Override the path with
  `HANDY_TRANSCRIBE_BIN` or `handyTranscribeBin` in the config.
- `python3` (3.9+) — used by the note stage.
- `yt-dlp` + `ffmpeg` — only needed when the input is a URL.
- An OpenAI-compatible LLM key — only needed for the polished mode (`--raw` never calls a model).

## Usage

```bash
# 1) transcript only (cached; repeat runs are instant)
scripts/transcribe.sh "https://www.youtube.com/watch?v=..."
scripts/transcribe.sh ./meeting.m4a -o meeting.txt
scripts/transcribe.sh ./lecture.wav --model Qwen3-ASR-1.7B -l zh --json

# 2) transcript + polished note filed into the notes folder
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./recording.m4a --vault "$HOME/Documents/Obsidian Vault" --base Resources

# 3) transcript + verbatim note, no LLM at all
scripts/to-obsidian.sh ./lecture.mp4 --raw
scripts/to-obsidian.sh ./meeting.m4a --raw --vault ~/notes/inbox
```

Anything after the input (or after `--`) is passed straight through to `handy-transcribe`:

> If the scripts arrived without the executable bit (some package managers drop it), either
> `chmod +x scripts/*.sh` or invoke them as `bash scripts/transcribe.sh …`.

| Option | Meaning |
|---|---|
| `-m, --model <id\|path>` | catalog model id (`Qwen3-ASR-1.7B`, `whisper-large-v3-turbo`, `SenseVoiceSmall`, `parakeet-tdt-0.6b-v3`, …) or a local `.gguf` |
| `-q, --quant <q>` | `F32`/`F16`/`Q8_0`/`Q5_K_M`/… (default `Q8_0`) |
| `-l, --language <code>` | language hint (`en`, `zh`, `ja`, …); default auto-detect |
| `--translate` | translate the result to English |
| `--no-chunk` | disable VAD chunking (whole file in one pass) |
| `--keep-fillers` | keep "uh"/"um" |
| `--custom-words <file>` | vocabulary file to bias spelling of names/jargon |
| `--json` | machine-readable output with backend, RTF, detected language |
| `-o, --output <file>` | write to a file |

## Choosing the model

The model is resolved in this order:

1. an explicit `--model` / `-m` (and `--quant` / `-q`) on the command line;
2. `model` / `quant` in the config — `transcribe.sh` injects them and says so on stderr
   (`model: Qwen3-ASR-0.6B (from config)`);
3. `handy-transcribe`'s own default: `Qwen3-ASR-0.6B`, `Q8_0`.

Rules to follow:

- **Say what you are using.** In your first message name the model, and if it is not downloaded yet,
  its size: "transcribing with Qwen3-ASR-0.6B (850 MB, first run)".
- **Ask once before a large download.** If the model is not cached and is bigger than ~300 MB, ask the
  user before starting. Check with `scripts/doctor.sh` (it prints the configured model and whether it
  is cached) or `handy-transcribe --list-models` (`✓` = cached). Do not ask again for that model on
  that machine.
- **Pick by content and hardware** when the user has no preference and nothing is configured:

  | Content / machine | Model | Download | Why |
  |---|---|---|---|
  | Chinese, Japanese, Korean, or mixed | `Qwen3-ASR-0.6B` | 850 MB | strongest on CJK, still quick on CPU |
  | Accuracy matters most, Apple Silicon or GPU | `Qwen3-ASR-1.7B` | 2.2 GB | best quality, needs headroom |
  | English only | `parakeet-tdt-0.6b-v3` | 740 MB | English-specialised, fast |
  | Weak CPU / long audio / speed-critical | `SenseVoiceSmall` | 253 MB | tiny and very fast |
  | Anything else | `Qwen3-ASR-0.6B` | 850 MB | safe default |

- **Check the catalog instead of guessing.** `handy-transcribe --list-models --language <code>` lists
  every model that supports a language, smallest first (add `--json` for languages/capabilities), and
  a run warns when `-l` names a language the selected model does not list.
- **Persist the choice** once the user agrees: add `"model": "…"` (and optionally `"quant": "Q8_0"`)
  to the config so later runs do not ask again.

## Configuration

Optional JSON config, read from `$MEDIA_TRANSCRIBE_CONFIG` or
`${XDG_CONFIG_HOME:-~/.config}/pi-media-transcribe/config.json`. See `config.example.json`.

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "baseSubdir": "Resources",
  "locale": "auto",
  "tags": ["auto-transcribed"],
  "llm": { "baseUrl": "https://api.deepseek.com", "model": "deepseek-chat", "apiKeyEnv": "DEEPSEEK_API_KEY" },
  "frontmatter": { "createdField": "created_at", "modifiedField": "last_modify_at" },
  "headings": { "source": "Source", "summary": "Core ideas", "body": "Transcript" }
}
```

- `vault` — notes folder root: an Obsidian vault **or any directory**. Resolution order: `--vault` →
  `$OBSIDIAN_VAULT` → config → the vault Obsidian itself has open (read from `obsidian.json`) →
  `~/Documents/Obsidian Vault`.
- `baseSubdir` — restrict the LLM's folder choice to this subtree. Empty means the whole folder.
- `locale` — `auto` guesses the note's heading language from the transcript's script and writes the
  body in the transcript's language. Pins: `en`, `zh`, `ja`, `ko`, `ru`, `de`, `es`, `fr`, `pt`;
  other scripts keep English labels (override with `headings`).
- `tags` — tags always added; 1–3 topic tags are chosen by the LLM on top.
- `llm` — any OpenAI-compatible chat endpoint. Keys are provider-bound: `llm.provider` (or the host of
  `llm.baseUrl`) decides which `$PROVIDER_API_KEY` or stored `~/.pi/agent/auth.json` credential is
  used, and a key belonging to another provider is never sent — the run fails with an explanation
  instead. A local server (`http://localhost:11434/v1` for Ollama, `:1234` for LM Studio) keeps the
  whole pipeline — transcription *and* polishing — on the machine and needs no key.

## What the note looks like
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
### <topic heading>
<proofread, segmented body>
```

The LLM may only pick a folder from the list it is shown, and the path is validated against the notes
folder root, so a bad model reply cannot write outside it. Existing notes are never overwritten: a
numeric suffix is added (`--overwrite` to replace).

**Long recordings**: transcripts under `llm.maxDirectChars` (default 48 000 characters) go to the model
in a single request. Longer ones are compressed chunk by chunk (`llm.chunkChars`, default 24 000) and
then merged into one article, so a multi-hour recording still works; each chunk is one extra request.

**Failure behaviour**: if the LLM step fails (no key, no credit, context overflow, network), the raw
transcript is still written as a note and the command warns about it. Re-running the same command
reuses the cached transcript, so only the LLM step is retried.

## Caching

Transcripts are cached per input + options in `~/.cache/pi-media-transcribe/transcripts/`. Re-running
the same video with `to-obsidian.sh` therefore reuses the transcript and only re-runs the LLM.
`NO_CACHE=1` forces a fresh transcription; `MEDIA_TRANSCRIBE_CACHE` moves the cache.

## Troubleshooting

- **`yt-dlp` fails / times out** → network restrictions. Configure a proxy
  (`export https_proxy=http://127.0.0.1:7890`), or download the audio yourself and pass the local file.
- **Model download stalls** → models come from Hugging Face. Point `HF_ENDPOINT` at a mirror, e.g.
  `export HF_ENDPOINT=https://hf-mirror.com`; the SHA-256 check still applies.
- **`handy-transcribe not found`** → run `scripts/doctor.sh`; it prints the install command.
- **`401` / `402` from the LLM** → wrong API key or no credit; check `llm.apiKeyEnv`, or use `--raw`.
- **`413` / context overflow** → lower `llm.maxDirectChars` and `llm.chunkChars` in the config.
- **Note has no folder / went to the root** → the notes folder has no candidate folders; set
  `baseSubdir` or create one.
- **Empty transcript** → no speech detected, or a silent/ambient-only recording.

## Limits

- Audio only: no on-screen text, slides, or frame understanding.
- The polished mode costs tokens: one request for a normal recording, one per chunk plus one merge for
  very long ones. `--raw` costs nothing and stays fully offline.
- `--raw` output is the transcript verbatim, ASR mistakes included.
- bash + Python 3.9+ on macOS/Linux; on Windows use WSL or Git Bash.
