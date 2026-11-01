# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.4] - 2026-11-01

### Changed

- `doctor.sh` no longer hardcodes which model suits which OS. It reads
  `handy-transcribe --list-models --json` and reports the model in use (size, supported languages,
  cache state) plus the three smallest models for the language of the notes — taken from the pinned
  `locale`, else the system `LANG`, else English. Builds older than 0.1.2 fall back to a rule of
  thumb with an upgrade hint.

### Fixed

- The language fallback compared against `[A-Z]` in a `case` pattern, which also matches lowercase
  under `LANG=zh_CN.UTF-8`, silently downgrading the recommendation to English.

## [0.2.3] - 2026-11-01

### Added

- `model` and `quant` config keys: `transcribe.sh` injects them when no `--model` / `--quant` is given
  on the command line, so a machine has one stable ASR default instead of a per-run choice. Explicit
  flags still win, and injection is reported on stderr (`model: … (from config)`).
- `doctor.sh` now reports the transcription model in use, whether it is cached locally, and a
  language/hardware-based recommendation.
- `SKILL.md` gained a "Choosing the model" section: state the model and its download size before the
  first run, ask once before a download larger than ~300 MB, pick by content/hardware when the user has
  no preference, and persist the choice to the config.

### Changed

- Badges now read the published npm version; the install line no longer says "once published".

## [0.2.2] - 2026-11-01

### Changed

- READMEs restructured: centred logo, title, language switcher and a shields.io badge row, followed
  by a scannable feature list and a real terminal demo.
- Added Japanese (`README.ja.md`) and Korean (`README.ko.md`) translations next to English and
  Simplified Chinese; CI now fails if a language switcher or the logo link goes missing.

### Added

- `assets/logo.svg` — a simple waveform mark used at the top of every README.

## [0.2.1] - 2026-11-01

### Added

- Nine heading languages (`en`, `zh`, `ja`, `ko`, `ru`, `de`, `es`, `fr`, `pt`) instead of two, plus
  per-language default tags. The heading language is inferred from the transcript's script (kana →
  Japanese, hangul → Korean, CJK → Chinese, Cyrillic → Russian, …) or pinned with `--locale`.
- Documentation for pointing `llm` at OpenAI, OpenRouter, Ollama or LM Studio, so the whole pipeline
  can stay on the machine.
- `doctor.sh` reports platform notes and the resolved interpreter.

### Changed

- `python3` is no longer a hard requirement: `python` is used when that is all a system provides
  (common on Windows/Git Bash).

### Fixed

- Notes no longer land in the notes-folder root when the LLM returns no folder: the configured
  `baseSubdir` is used as the fallback, and the base folder itself is now offered as a candidate.
- Unsupported scripts/locales no longer raise `KeyError` while picking headings.
- The transcript cache key no longer depends on `stat -f`/`stat -c` (their flags mean different things
  on BSD and GNU), so caching is stable across platforms.

## [0.2.0] - 2026-11-01

### Added

- `--raw` / `--no-llm` mode: write the transcript verbatim as a note without calling an LLM. No API
  key, no token cost, fully offline — the transcription-only and polishing paths are now separable.
- Map-reduce pass for long recordings: transcripts longer than `llm.maxDirectChars` (default 48 000
  characters) are compressed in `llm.chunkChars` chunks (default 24 000) and merged into one article,
  so multi-hour podcasts no longer overflow the model's context window.
- Verbatim notes fall back automatically when the LLM step fails, so a failed polish never loses the
  transcript.

### Changed

- Repositioned: notes are “Markdown notes, Obsidian-ready”, not Obsidian-only. `--vault` accepts any
  directory, and the docs/config say so.
- `--raw`/`--no-llm` and `--overwrite` are now first-class flags of `to-obsidian.sh`.

### Fixed

- The map-reduce prompt no longer raises `KeyError` when formatting its index/total placeholders.

## [0.1.0] - 2026-10-31

### Added

- First publishable release of the `media-transcribe` Pi skill, packaged as an npm-installable Pi
  package (`pi install npm:pi-media-transcribe`).
- `scripts/transcribe.sh` — URL or local file → transcript, with an on-disk transcript cache keyed by
  input + options, `NO_CACHE=1` to bypass it, and actionable errors when `yt-dlp`/`ffmpeg`/
  `handy-transcribe` are missing.
- `scripts/to-obsidian.sh` — transcript → LLM proofread/segment/summarize → Markdown note filed in the
  vault.
- `scripts/doctor.sh` — environment report (ASR binary, python, yt-dlp/ffmpeg, LLM key, vault,
  candidate folders, cache size).
- JSON configuration (`~/.config/pi-media-transcribe/config.json`): vault, `baseSubdir`, `locale`,
  `tags`, LLM endpoint/model/key variable, frontmatter field names, section headings, ASR binary path.
- Vault autodetection: `--vault` → `$OBSIDIAN_VAULT` → config → Obsidian's own `obsidian.json` →
  `~/Documents/Obsidian Vault`.
- Notes follow the transcript's language (including headings) instead of being hard-coded to Chinese.
- Path-traversal guard: the LLM may only pick from the offered folders, and the final path is
  validated against the vault root.
- Notes with a duplicate title get a numeric suffix instead of being overwritten (`--overwrite` to
  force).
- LLM calls retry once on 429/5xx and surface actionable messages for 401/402/404.
