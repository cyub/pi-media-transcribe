#!/usr/bin/env bash
# Environment check for the media-transcribe skill: prints what is ready and
# exactly what to install or configure for everything that is not.
#
# Usage: doctor.sh [--vault <path>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_lib.sh
source "$SCRIPT_DIR/_lib.sh"

ok() { printf '  \033[32m✓\033[0m %s\n' "$*"; }
no() { printf '  \033[31m✗\033[0m %s\n' "$*"; }
note() { printf '    → %s\n' "$*"; }

vault_arg=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault) vault_arg="${2:?}"; shift 2 ;;
    --vault=*) vault_arg="${1#--vault=}"; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done

echo "pi-media-transcribe doctor"
echo
echo "config: $CONFIG_FILE"
[[ -f "$CONFIG_FILE" ]] && ok "config present" || note "not found — defaults are used (optional)"
echo

echo "core tools"
python_bin="$(resolve_python)"
if [[ -n "$python_bin" ]]; then
  py_version="$("$python_bin" -c 'import sys;print("%d.%d.%d" % sys.version_info[:3])')"
  py_major="$("$python_bin" -c 'import sys;print(sys.version_info[0])')"
  py_minor="$("$python_bin" -c 'import sys;print(sys.version_info[1])')"
  if [[ "$py_major" -eq 3 && "$py_minor" -ge 9 ]]; then
    ok "python: $python_bin $py_version"
  else
    no "python $py_version is too old (need 3.9+)"
    note "brew install python@3.12 | sudo apt install python3"
  fi
else
  no "python3 missing"
  note "install Python 3.9+ (brew install python@3.12 | apt install python3)"
fi

handy="$(resolve_handy)"
if [[ -n "$handy" ]]; then
  version="$("$handy" --version 2>/dev/null | head -1 || echo 'version unknown')"
  ok "handy-transcribe: $handy ($version)"
else
  no "handy-transcribe not found"
  note "cargo install handy-transcribe   (or cargo binstall handy-transcribe)"
  note "prebuilt binaries: https://github.com/cyub/handy-transcribe/releases"
fi
echo

echo "transcription model"
cfg_model="$(config_get model "")"
cfg_quant="$(config_get quant "")"
used_model="${cfg_model:-Qwen3-ASR-0.6B}"
if [[ -n "$cfg_model" ]]; then
  ok "configured: $cfg_model${cfg_quant:+ (quant $cfg_quant)}"
else
  note "not configured — handy-transcribe default: $used_model (add \"model\" to $CONFIG_FILE to pin it)"
fi
# Which language should the recommendation cover? The pinned note language, else the
# system locale, else English.
rec_lang="$(config_get locale "")"
case "$rec_lang" in "" | auto) rec_lang="${LANG%%_*}" ;; esac
# Only the languages this skill writes headings for are candidates; anything else falls back to
# English. (A plain [A-Z] range is locale-dependent here — under LANG=zh_CN it also matches "zh".)
rec_lang="$(printf '%s' "$rec_lang" | tr '[:upper:]' '[:lower:]')"
case "$rec_lang" in
  en | zh | ja | ko | ru | de | es | fr | pt) ;;
  *) rec_lang="en" ;;
esac

catalog_ok=0
if [[ -n "$handy" ]] && "$handy" --list-models --json >/dev/null 2>&1; then
  catalog_ok=1
  # Read the catalog instead of hardcoding a table: it knows languages, sizes and cache state.
  "$PYTHON" - "$handy" "$used_model" "$rec_lang" <<'PY'
import json, subprocess, sys

exe, model_id, lang = sys.argv[1], sys.argv[2], sys.argv[3]
OK, DIM, RESET = "\033[32m✓\033[0m", "    → ", ""


def listing(*args):
    proc = subprocess.run([exe, "--list-models", *args, "--json"],
                          capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []


me = next((m for m in listing() if m["id"] == model_id), None)
if me:
    langs = me.get("languages") or []
    shown = ", ".join(langs[:8]) + (f" (+{len(langs) - 8} more)" if len(langs) > 8 else "")
    print(f"  {OK if me.get('cached') else ' '} {me['size_mb']:>5} MB  {model_id} — in use")
    print(f"{DIM}supports: {shown or '-'}")
    if not me.get("cached"):
        print(f"{DIM}not cached yet: the first run downloads it")
else:
    print(f"  ? {model_id} is not in this catalog version")

for candidate in listing("--language", lang)[:3]:
    print(f"  {OK if candidate.get('cached') else ' '} {candidate['size_mb']:>5} MB  "
          f"{candidate['id']}  ← smallest for {lang}")
print(f"{DIM}other languages: handy-transcribe --list-models --language <code>")
PY
fi

if [[ $catalog_ok -eq 0 ]]; then
  note "this handy-transcribe build cannot list languages; upgrade for sized recommendations"
  case "$(uname -s)" in
    Darwin) note "rule of thumb: Qwen3-ASR-0.6B for zh/ja/ko, Qwen3-ASR-1.7B for maximum accuracy" ;;
    *) note "rule of thumb: Qwen3-ASR-0.6B, or SenseVoiceSmall for speed on weak CPUs" ;;
  esac
fi
echo

echo "media download (only needed for URL input)"
for tool in yt-dlp ffmpeg; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool $(command -v "$tool")"
  else
    no "$tool missing"
    case "$tool" in
      yt-dlp) note "brew install yt-dlp | pipx install yt-dlp | scoop install yt-dlp" ;;
      ffmpeg) note "brew install ffmpeg | apt install ffmpeg | scoop install ffmpeg" ;;
    esac
  fi
done
echo

echo "LLM (used by to-obsidian.sh)"
llm_key_env="$(config_get llm.apiKeyEnv "")"
if [[ -n "${LLM_API_KEY:-}" ]]; then
  ok "LLM_API_KEY is set"
elif [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  ok "DEEPSEEK_API_KEY is set"
elif [[ -n "$llm_key_env" && -n "$(printenv "$llm_key_env" 2>/dev/null || true)" ]]; then
  ok "${llm_key_env} is set"
elif [[ -f "$HOME/.pi/agent/auth.json" ]] && grep -q '"key"' "$HOME/.pi/agent/auth.json" 2>/dev/null; then
  ok "falling back to ~/.pi/agent/auth.json"
else
  no "no LLM API key"
  note "export LLM_API_KEY=sk-...   (any OpenAI-compatible endpoint; see config.example.json)"
fi
ok "endpoint: $(config_get llm.baseUrl "https://api.deepseek.com")  model: $(config_get llm.model "deepseek-chat")"
echo

echo "notes folder"
print_vault_args=()
[[ -n "$vault_arg" ]] && print_vault_args+=(--vault "$vault_arg")
[[ -f "$CONFIG_FILE" ]] && print_vault_args+=(--config "$CONFIG_FILE")
# bash 3.2 (macOS) treats an empty array expansion as unbound under set -u.
resolved="$("$PYTHON" "$SCRIPTS_DIR/llm_to_obsidian.py" --print-vault ${print_vault_args[@]+"${print_vault_args[@]}"} 2>/dev/null || true)"
if [[ -n "$resolved" && -d "$resolved" ]]; then
  ok "notes folder: $resolved"
  base="$(config_get baseSubdir "")"
  folders="$("$PYTHON" -c '
import sys
from pathlib import Path
vault, base = Path(sys.argv[1]), sys.argv[2]
root = vault / base if base else vault
print(sum(1 for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")) if root.is_dir() else 0)
' "$resolved" "$base")"
  if [[ "${folders:-0}" -gt 0 ]]; then
    ok "$folders candidate folders offered to the LLM${base:+ (under $base)}"
  else
    no "no candidate folders${base:+ under $base} — notes would be filed at the vault root"
    note "set \"baseSubdir\" in the config, or create a folder for notes"
  fi
else
  no "no notes folder detected"
  note "pass --vault PATH, export OBSIDIAN_VAULT, or set \"vault\" in the config (any directory works)"
fi
echo

echo "cache: $CACHE_DIR"
if [[ -d "$CACHE_DIR/transcripts" ]]; then
  ok "$(find "$CACHE_DIR/transcripts" -name '*.txt' | wc -l | tr -d ' ') cached transcripts"
else
  note "empty (first run will create it)"
fi
