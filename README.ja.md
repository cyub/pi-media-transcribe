<p align="center">
  <img src="assets/logo.svg" width="72" height="72" alt="pi-media-transcribe logo">
</p>

<h1 align="center">pi-media-transcribe</h1>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <strong>日本語</strong> ·
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

<p align="center">動画・音声を入れると、構造化された Markdown ノートが出てくる — 文字起こしはローカルで、ノートフォルダに直接保存。</p>

YouTube、ポッドキャスト、ウェビナー、会議録音、あるいはローカルのメディアファイルを、そのまま残しておきたい
ノートに変える [Pi](https://pi.dev) スキルパッケージです。文字起こしは**完全にオフライン**で手元のマシン上で
実行されます（Whisper / Qwen3-ASR / Parakeet / SenseVoice、
[`handy-transcribe`](https://github.com/cyub/handy-transcribe) を使用）。音声のアップロードも分単位の課金も
ありません。そのあと LLM が誤字を直し、見出しで区切り、要約を書きますが、これは任意です — `--raw` なら
モデルを一切呼びません。

- **ローカルファースト:** 音声はマシンの外に出ません。既定モデルは CPU で動き、API キーも不要です。
- **3 つの独立したモード:** 文字起こしのみ／原文のままノート化／整形してノート化。
- **ノートフォルダは自由:** Obsidian vault でも普通の Markdown フォルダでも可。frontmatter 付き。
- **見出しは 9 言語:** English、简体中文、日本語、한국어、Русский、Deutsch、Español、Français、Português。文字体系から自動判定します。
- **長い録音にも対応:** 通常の講演は 1 リクエスト、3 時間のポッドキャストは分割して要約・統合。
- **作業を失わない:** LLM の処理が失敗しても、生の文字起こしはノートとして保存されます。
- **モデルは選べる:** OpenAI、OpenRouter、DeepSeek、あるいはローカルの Ollama / LM Studio。

## デモ

```console
$ scripts/to-obsidian.sh "https://www.youtube.com/watch?v=Uz7K757psEU"
==> transcribing
==> correcting, segmenting, summarizing, filing
LLM: deepseek-chat via https://api.deepseek.com (note language: zh, 12 folders offered)
saved: 資料/02-人工智能/AI智能体/高阶Graph RAG：从向量检索困境到图谱增强推理.md
```

16 分の中国語技術講演が 18.8 KB のノート（要約 + 17 セクション）になります。文字起こし自体は Apple M1 Pro で
`Qwen3-ASR-0.6B` を使い 49 秒（実時間の約 20 倍速）。

## インストール

```bash
pi install npm:pi-media-transcribe
pi install ./pi-media-transcribe    # ローカルのチェックアウトから
```

必要なもの:

```bash
cargo install handy-transcribe     # オフライン ASR エンジン（cargo binstall でも可）
brew install yt-dlp ffmpeg         # URL 入力のときだけ必要
# ノート化の工程で python3 3.9+ を使用
```

まず環境チェック（足りないものと導入手順を表示します）:

```bash
skills/media-transcribe/scripts/doctor.sh
```

## 使い方

Pi に話しかける:

> 「この動画を文字起こしして、ノートに保存して: https://www.youtube.com/watch?v=...」

スクリプトを直接叩く:

```bash
# 文字起こしだけ（キャッシュされるので 2 回目以降は一瞬）
scripts/transcribe.sh "https://www.youtube.com/watch?v=..."
scripts/transcribe.sh ./meeting.m4a -o meeting.txt

# 文字起こし + 整形ノート（LLM）
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./recording.m4a --vault ~/Documents/Obsidian\ Vault --base Notes
scripts/to-obsidian.sh ./talk.wav --model Qwen3-ASR-1.7B -l ja

# 文字起こし + 原文のままノート（LLM なし・無料・オフライン）
scripts/to-obsidian.sh ./lecture.mp4 --raw
scripts/to-obsidian.sh ./meeting.m4a --raw --vault ~/notes/inbox
```

`handy-transcribe` へそのまま渡せるオプション: `-m/--model`、`-q/--quant`、`-l/--language`、
`--translate`、`--device`、`--no-chunk`、`--keep-fillers`、`--custom-words`、`--json`、`-o`。
ノート側のフラグ: `--raw`、`--vault`、`--base`、`--locale`、`--overwrite`。

> パッケージマネージャによっては実行権限が落ちます。その場合は `chmod +x scripts/*.sh` するか、
> `bash scripts/transcribe.sh …` として呼び出してください。

## 設定

任意です。[`config.example.json`](config.example.json) を
`~/.config/pi-media-transcribe/config.json` にコピーして編集します:

```json
{
  "vault": "~/Documents/Obsidian Vault",
  "baseSubdir": "Notes",
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
  "headings": { "source": "出典", "summary": "要点", "body": "本文" }
}
```

- **ノートフォルダ:** `--vault` → `$OBSIDIAN_VAULT` → 設定ファイル → Obsidian が開いている vault →
  `~/Documents/Obsidian Vault`。どのディレクトリでも構いません。
- **言語:** 本文は常に文字起こしの言語に従います。見出しは `en`/`zh`/`ja`/`ko`/`ru`/`de`/`es`/`fr`/`pt`
  に対応し、文字体系から自動判定します（かな→日本語、ハングル→韓国語、漢字→中国語、キリル→ロシア語）。
  それ以外は英語の見出しになり、`headings` で上書きできます。
- **他の LLM:** OpenAI 互換のエンドポイントなら何でも使えます。

```json
"llm": { "baseUrl": "https://api.openai.com", "model": "gpt-5-mini", "apiKeyEnv": "OPENAI_API_KEY" }
"llm": { "baseUrl": "https://openrouter.ai/api", "model": "anthropic/claude-sonnet-5", "apiKeyEnv": "OPENROUTER_API_KEY" }
"llm": { "baseUrl": "http://localhost:11434/v1", "model": "qwen3:8b", "apiKeyEnv": "OLLAMA_API_KEY" }
```

ローカルサーバー（Ollama / LM Studio / vLLM）なら、文字起こしも整形もマシンの外に出ません。Ollama は
キーを検証しないので、空でなければ何でも構いません。

- **転写モデル:** `model`/`quant` で ASR モデルを固定できます。`--model` を渡さないときは
  `transcribe.sh` が自動で注入するため、マシンごとに安定した既定値になります。初回はダウンロードが
  走ります（`Qwen3-ASR-0.6B` Q8_0 で約 850 MB）。`scripts/doctor.sh` で使用モデルとキャッシュ状況を確認できます。
- **長い録音:** `llm.maxDirectChars`（既定 48,000 文字）以下は 1 リクエスト。それを超えると
  `llm.chunkChars`（既定 24,000）ごとに圧縮してから統合します。
- **安全性:** LLM は提示されたフォルダからしか選べず、最終パスはノートフォルダ内か検証されます。同名の
  ノートは上書きせず連番を付けます（`--overwrite` で上書き）。

## 出力例

```markdown
---
created_at: 2026/10/31 22:14
last_modify_at: 2026/10/31 22:14
tags:
  - youtube
  - 自動文字起こし
  - RAG
  - knowledge-graph
---
出典：https://www.youtube.com/watch?v=...

## 要点
<150〜300 語の要約>

---

## 本文
### ベクトル検索の限界
<校正・整形された本文>
```

## 仕組み

```
URL ──yt-dlp──▶ 音声 ──▶ handy-transcribe（symphonia → Silero VAD → transcribe.cpp）
                                │
                        文字起こし（キャッシュ）
                                │
            LLM（任意）: 校正 → セクション分割 → 要約 → フォルダ/タグ選択
                                │
                      Markdown ノート（frontmatter + 要約 + 本文）
```

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `yt-dlp` が失敗／タイムアウト | プロキシを設定（`export https_proxy=http://127.0.0.1:7890`）、またはローカルファイルを渡す |
| モデルのダウンロードが止まる | モデルは Hugging Face から取得。ミラーや社内プロキシを `HF_ENDPOINT` に設定（例: `https://your-hub-mirror.example`、SHA-256 検証は継続） |
| `handy-transcribe not found` | `scripts/doctor.sh` を実行するか、`HANDY_TRANSCRIBE_BIN` で指定 |
| LLM が 401/402 | キーの誤り／残高不足。`llm.apiKeyEnv` を確認、または `--raw` を使う |
| 413／コンテキスト超過 | `llm.maxDirectChars` と `llm.chunkChars` を小さくする |
| ノートがフォルダ直下に保存された | 候補フォルダが無い状態。`baseSubdir` を設定するかフォルダを作成 |
| LLM が失敗したのにノートがある | 組み込みのフォールバックで生の文字起こしを保存した結果。再実行すれば整形を再試行します |

## 制限

- 音声のみ。スライドや画面内テキスト、フレーム理解は行いません。
- 整形モードはトークンを消費します（通常 1 リクエスト、超長尺は分割数＋統合 1 回）。`--raw` は無料で完全オフライン。
- `--raw` のノートは文字起こしそのまま（ASR の誤りも含む）で、校正は行いません。
- macOS / Linux では bash + Python 3.9+。Windows は WSL か Git Bash が必要です。

## ライセンス

MIT — [LICENSE](LICENSE) を参照。[Handy](https://github.com/cjpais/Handy) と
[transcribe.cpp](https://github.com/handy-computer/transcribe.cpp) の上に構築され、ASR CLI として
[handy-transcribe](https://github.com/cyub/handy-transcribe) を呼び出します。
