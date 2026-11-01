#!/usr/bin/env bash
# Transcribe a URL or local media file and file it as a Markdown note.
#
# Two modes:
#   default        transcript -> LLM (proofread, segment, summarise) -> note
#   --raw/--no-llm transcript -> note, verbatim (no API key, no token cost)
#
# If the LLM step fails, the raw transcript is still saved as a note so the work
# is never lost.
#
# Usage:
#   to-obsidian.sh <url | media-file> [--vault <path>] [--base <subdir>]
#                  [--raw|--no-llm] [--overwrite] [--] [transcribe options...]
#
# Examples:
#   to-obsidian.sh "https://www.youtube.com/watch?v=..."
#   to-obsidian.sh ./recording.m4a --vault "$HOME/Documents/Obsidian Vault" --base Resources
#   to-obsidian.sh ./meeting.m4a --raw                 # offline, no LLM
#   to-obsidian.sh "https://youtu.be/..." --model Qwen3-ASR-1.7B -l zh
#
# Env:
#   OBSIDIAN_VAULT   notes folder when --vault is omitted ($HOME must be set)
#   LLM_API_KEY / DEEPSEEK_API_KEY, LLM_BASE_URL, LLM_MODEL   LLM credentials
#   MEDIA_TRANSCRIBE_CONFIG   path to config.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_lib.sh
source "$SCRIPT_DIR/_lib.sh"

usage() {
  cat >&2 <<'EOF'
Usage: to-obsidian.sh <url | media-file> [--vault <path>] [--base <subdir>]
                      [--raw|--no-llm] [--overwrite] [--] [transcribe options...]

Transcribes (reusing the transcript cache), then writes a Markdown note.
  --raw / --no-llm   skip the LLM: keep the transcript verbatim, no API key needed
  --vault PATH       notes folder (any directory; defaults to the Obsidian vault)
  --base SUBDIR      file notes under this subfolder of the notes folder
EOF
}

main() {
  [[ $# -ge 1 ]] || {
    usage
    exit 2
  }
  local input="$1"
  shift

  local vault="" base="" raw=0 overwrite=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vault)
        vault="${2:?--vault needs a path}"
        shift 2
        ;;
      --vault=*)
        vault="${1#--vault=}"
        shift
        ;;
      --base)
        base="${2:?--base needs a subdirectory}"
        shift 2
        ;;
      --base=*)
        base="${1#--base=}"
        shift
        ;;
      --raw | --no-llm)
        raw=1
        shift
        ;;
      --overwrite)
        overwrite=1
        shift
        ;;
      *) break ;;
    esac
  done
  [[ "${1:-}" == "--" ]] && shift

  PYTHON="$(require_python)"

  if [[ $raw -eq 0 && -z "$(config_get llm.apiKeyEnv "")" && -z "${LLM_API_KEY:-}${DEEPSEEK_API_KEY:-}" ]]; then
    info "no LLM_API_KEY/DEEPSEEK_API_KEY in the environment; will fall back to ~/.pi/agent/auth.json (use --raw to skip the LLM)."
  fi

  info "==> transcribing"
  local transcript
  transcript="$("$SCRIPT_DIR/transcribe.sh" "$input" "$@")"
  [[ -n "${transcript//[[:space:]]/}" ]] || die "transcript is empty — is there speech in this file?"

  local args=("$input")
  [[ -n "$vault" ]] && args+=(--vault "$vault")
  [[ -n "$base" ]] && args+=(--base "$base")
  [[ $overwrite -eq 1 ]] && args+=(--overwrite)

  if [[ $raw -eq 1 ]]; then
    # Give the note a human-readable name: the real video title when cheaply available.
    if is_url "$input" && command -v yt-dlp >/dev/null 2>&1; then
      local fetched_title
      fetched_title="$(yt-dlp --no-update --skip-download --socket-timeout 10 --print '%(title)s' "$input" 2>/dev/null | head -1 || true)"
      [[ -n "$fetched_title" ]] && args+=(--title "$fetched_title")
    fi
    info "==> writing the note (raw mode: no LLM)"
    printf '%s\n' "$transcript" | "$PYTHON" "$SCRIPT_DIR/llm_to_obsidian.py" "${args[@]}" --raw
    return
  fi

  info "==> correcting, segmenting, summarizing, filing"
  if printf '%s\n' "$transcript" | "$PYTHON" "$SCRIPT_DIR/llm_to_obsidian.py" "${args[@]}"; then
    return
  fi

  warn "LLM step failed — saving the raw transcript instead so nothing is lost."
  warn "retry later with the same command (the transcript is cached), or pass --raw to skip the LLM."
  printf '%s\n' "$transcript" | "$PYTHON" "$SCRIPT_DIR/llm_to_obsidian.py" "${args[@]}" --raw
}

main "$@"
