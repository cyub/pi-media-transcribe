# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
