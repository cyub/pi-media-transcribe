<p align="center">
  <img src="assets/logo.svg" width="72" height="72" alt="pi-media-transcribe logo">
</p>

<h1 align="center">pi-media-transcribe</h1>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <strong>한국어</strong>
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

<p align="center">동영상·음성을 넣으면 구조화된 Markdown 노트가 나옵니다 — 전사는 로컬에서, 노트 폴더에 바로 저장.</p>

YouTube 영상, 팟캐스트, 웨비나, 회의 녹음, 또는 로컬 미디어 파일을 남겨두고 싶은 노트로 바꿔주는
[Pi](https://pi.dev) 스킬 패키지입니다. 전사는 **완전히 오프라인**으로 내 컴퓨터에서 실행됩니다
(Whisper / Qwen3-ASR / Parakeet / SenseVoice, 기반은
[`handy-transcribe`](https://github.com/cyub/handy-transcribe)) — 오디오 업로드도, 분당 과금도 없습니다.
이후 LLM이 오타를 고치고 소제목으로 나누고 요약을 씁니다. 다만 이 단계는 선택입니다 — `--raw`를 쓰면
모델을 전혀 호출하지 않습니다.

- **로컬 우선:** 오디오가 기기 밖으로 나가지 않습니다. 기본 모델은 CPU에서 돌고 API 키도 필요 없습니다.
- **세 가지 분리된 모드:** 전사만 / 원문 그대로 노트 / 다듬어서 노트.
- **노트 폴더는 자유:** Obsidian vault든 일반 Markdown 폴더든 상관없습니다. frontmatter 포함.
- **소제목 9개 언어:** English, 简体中文, 日本語, 한국어, Русский, Deutsch, Español, Français, Português — 문자 체계로 자동 판별.
- **긴 녹음 지원:** 일반 강연은 요청 1회, 3시간 팟캐스트는 분할 요약 후 병합.
- **작업을 잃지 않음:** LLM 단계가 실패해도 원본 전사는 노트로 저장됩니다.
- **모델 선택 가능:** OpenAI, OpenRouter, DeepSeek, 또는 로컬 Ollama / LM Studio.

## 데모

```console
$ scripts/to-obsidian.sh "https://www.youtube.com/watch?v=Uz7K757psEU"
==> transcribing
==> correcting, segmenting, summarizing, filing
LLM: deepseek-chat via https://api.deepseek.com (note language: zh, 12 folders offered)
saved: 資料/02-人工智能/AI智能体/高阶Graph RAG：从向量检索困境到图谱增强推理.md
```

16분짜리 중국어 기술 강연이 18.8 KB 노트(요약 + 17개 섹션)가 됩니다. 전사 자체는 Apple M1 Pro에서
`Qwen3-ASR-0.6B`로 49초(실시간 대비 약 20배) 걸렸습니다.

## 설치

```bash
pi install npm:pi-media-transcribe
pi install ./pi-media-transcribe    # 로컬 체크아웃에서
```

필요한 것:

```bash
cargo install handy-transcribe     # 오프라인 ASR 엔진 (cargo binstall 도 가능)
brew install yt-dlp ffmpeg         # URL 입력일 때만 필요
# 노트 작성 단계에서 python3 3.9+ 사용
```

먼저 환경 점검 — 빠진 것과 설치 방법을 알려줍니다:

```bash
skills/media-transcribe/scripts/doctor.sh
```

## 사용법

Pi에게 말하기:

> "이 영상 전사해서 내 노트에 저장해줘: https://www.youtube.com/watch?v=..."

스크립트를 직접 호출:

```bash
# 전사만 (캐시되므로 두 번째부터는 즉시)
scripts/transcribe.sh "https://www.youtube.com/watch?v=..."
scripts/transcribe.sh ./meeting.m4a -o meeting.txt

# 전사 + 다듬은 노트 (LLM)
scripts/to-obsidian.sh "https://www.youtube.com/watch?v=..."
scripts/to-obsidian.sh ./recording.m4a --vault ~/Documents/Obsidian\ Vault --base Notes
scripts/to-obsidian.sh ./talk.wav --model Qwen3-ASR-1.7B -l ko

# 전사 + 원문 그대로 노트 (LLM 없음, 무료, 오프라인)
scripts/to-obsidian.sh ./lecture.mp4 --raw
scripts/to-obsidian.sh ./meeting.m4a --raw --vault ~/notes/inbox
```

`handy-transcribe`로 그대로 전달되는 옵션: `-m/--model`, `-q/--quant`, `-l/--language`,
`--translate`, `--device`, `--no-chunk`, `--keep-fillers`, `--custom-words`, `--json`, `-o`.
노트 관련 플래그: `--raw`, `--vault`, `--base`, `--locale`, `--overwrite`.

> 패키지 관리자에 따라 실행 권한이 사라질 수 있습니다. 그럴 때는 `chmod +x scripts/*.sh` 하거나
> `bash scripts/transcribe.sh …` 형태로 호출하세요.

## 설정

선택 사항입니다. [`config.example.json`](config.example.json)을
`~/.config/pi-media-transcribe/config.json`으로 복사해서 수정하세요:

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
  "headings": { "source": "출처", "summary": "핵심 내용", "body": "본문" }
}
```

- **노트 폴더:** `--vault` → `$OBSIDIAN_VAULT` → 설정 파일 → Obsidian이 열고 있는 vault →
  `~/Documents/Obsidian Vault`. 아무 디렉터리나 가능합니다.
- **언어:** 본문은 항상 전사 언어를 따릅니다. 소제목은 `en`/`zh`/`ja`/`ko`/`ru`/`de`/`es`/`fr`/`pt`를
  지원하며 문자 체계로 자동 판별합니다(가나→일본어, 한글→한국어, 한자→중국어, 키릴→러시아어).
  그 외 문자 체계는 영어 소제목이 되며 `headings`로 덮어쓸 수 있습니다.
- **다른 LLM:** OpenAI 호환 엔드포인트면 무엇이든 됩니다.

```json
"llm": { "baseUrl": "https://api.openai.com", "model": "gpt-5-mini", "apiKeyEnv": "OPENAI_API_KEY" }
"llm": { "baseUrl": "https://openrouter.ai/api", "model": "anthropic/claude-sonnet-5", "apiKeyEnv": "OPENROUTER_API_KEY" }
"llm": { "baseUrl": "http://localhost:11434/v1", "model": "qwen3:8b", "apiKeyEnv": "OLLAMA_API_KEY" }
```

로컬 서버(Ollama / LM Studio / vLLM)를 쓰면 전사와 다듬기 모두 기기 밖으로 나가지 않습니다. Ollama는
키를 검사하지 않으므로 비어 있지 않은 아무 값이나 넣으면 됩니다.

- **전사 모델:** `model`/`quant`로 ASR 모델을 고정합니다. `--model`을 넘기지 않으면 `transcribe.sh`가
  자동으로 주입하므로 머신마다 안정적인 기본값이 됩니다. 첫 실행 시 다운로드됩니다
  (`Qwen3-ASR-0.6B` Q8_0 기준 약 850 MB). `scripts/doctor.sh`에서 사용 모델과 캐시 여부를 확인할 수 있습니다.
- **긴 녹음:** `llm.maxDirectChars`(기본 48,000자) 이하는 요청 1회. 그보다 길면 `llm.chunkChars`
  (기본 24,000자) 단위로 압축한 뒤 병합합니다.
- **안전성:** LLM은 제시된 폴더에서만 고를 수 있고, 최종 경로는 노트 폴더 안인지 검증됩니다. 같은 이름의
  노트는 덮어쓰지 않고 번호를 붙입니다(`--overwrite`로 강제).

## 결과물 예시

```markdown
---
created_at: 2026/10/31 22:14
last_modify_at: 2026/10/31 22:14
tags:
  - youtube
  - 자동-전사
  - RAG
  - knowledge-graph
---
출처: https://www.youtube.com/watch?v=...

## 핵심 내용
<150~300단어 요약>

---

## 본문
### 벡터 검색의 한계
<교정·구획된 본문>
```

## 동작 방식

```
URL ──yt-dlp──▶ 오디오 ──▶ handy-transcribe (symphonia → Silero VAD → transcribe.cpp)
                                  │
                            전사 텍스트 (캐시)
                                  │
              LLM(선택): 교정 → 구획 → 요약 → 폴더/태그 선택
                                  │
                        Markdown 노트 (frontmatter + 요약 + 본문)
```

## 문제 해결

| 증상 | 해결 |
|---|---|
| `yt-dlp` 실패/타임아웃 | 프록시 설정(`export https_proxy=http://127.0.0.1:7890`) 또는 로컬 파일 전달 |
| 모델 다운로드가 멈춤 | 모델은 Hugging Face에서 받습니다. 미러나 사내 프록시를 `HF_ENDPOINT`에 지정하세요(예: `https://your-hub-mirror.example`, SHA-256 검증 유지) |
| `handy-transcribe not found` | `scripts/doctor.sh` 실행, 또는 `HANDY_TRANSCRIBE_BIN` 지정 |
| LLM이 401/402 | 키 오류/잔액 부족. `llm.apiKeyEnv` 확인 또는 `--raw` 사용 |
| 413/컨텍스트 초과 | `llm.maxDirectChars`와 `llm.chunkChars`를 줄이기 |
| 노트가 폴더 최상위에 저장됨 | 후보 폴더가 없음. `baseSubdir` 설정 또는 폴더 생성 |
| LLM은 실패했는데 노트가 있음 | 내장 폴백이 원본 전사를 저장한 것. 같은 명령을 다시 실행하면 다듬기만 재시도 |

## 제한

- 오디오만 처리합니다. 슬라이드, 화면 텍스트, 프레임 이해는 하지 않습니다.
- 다듬기 모드는 토큰을 사용합니다(일반 녹음 1회, 초장시간은 분할 수 + 병합 1회). `--raw`는 무료이며 완전 오프라인.
- `--raw` 노트는 전사 그대로이며 ASR 오류도 포함됩니다(교정 없음).
- macOS/Linux에서는 bash + Python 3.9+. Windows는 WSL 또는 Git Bash가 필요합니다.

## 라이선스

MIT — [LICENSE](LICENSE) 참고. [Handy](https://github.com/cjpais/Handy)와
[transcribe.cpp](https://github.com/handy-computer/transcribe.cpp) 위에 만들어졌고, ASR CLI로
[handy-transcribe](https://github.com/cyub/handy-transcribe)를 호출합니다.
