#!/usr/bin/env bash
# Download the audio of a YouTube video (or any yt-dlp supported URL, or a local
# media file) and transcribe it with handy-transcribe. Transcripts are cached, so
# re-running the same input does not re-download or re-transcribe.
#
# Usage:
#   transcribe.sh <youtube-url | media-file> [--] [handy-transcribe options...]
#
# Examples:
#   transcribe.sh "https://www.youtube.com/watch?v=..."
#   transcribe.sh "https://www.youtube.com/watch?v=..." --model Qwen3-ASR-1.7B --json
#   transcribe.sh ./local-video.m4a -l zh
#   NO_CACHE=1 transcribe.sh ./meeting.m4a          # bypass the transcript cache
#
# Env:
#   HANDY_TRANSCRIBE_BIN   path to the handy-transcribe binary
#   MEDIA_TRANSCRIBE_CACHE cache directory (default ~/.cache/pi-media-transcribe)
#   NO_CACHE=1             ignore cached transcripts for this run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_lib.sh
source "$SCRIPT_DIR/_lib.sh"

usage() {
  cat >&2 <<'EOF'
Usage: transcribe.sh <youtube-url | media-file> [--] [handy-transcribe options...]

Downloads audio with yt-dlp when given a URL, then transcribes with handy-transcribe.
Transcripts are cached under ~/.cache/pi-media-transcribe/transcripts.
EOF
}

main() {
  [[ $# -ge 1 ]] || {
    usage
    exit 2
  }
  local input="$1"
  shift
  [[ "${1:-}" == "--" ]] && shift

  local handy
  handy="$(require_handy)"

  # Explicit CLI flags always win; otherwise fall back to the configured model/quant so a
  # machine's default is stable and visible instead of being guessed on every run.
  local has_model=0 has_quant=0 arg
  for arg in "$@"; do
    case "$arg" in
      -m | --model | --model=*) has_model=1 ;;
      -q | --quant | --quant=*) has_quant=1 ;;
    esac
  done
  if [[ $has_model -eq 0 ]]; then
    local cfg_model
    cfg_model="$(config_get model "")"
    if [[ -n "$cfg_model" ]]; then
      set -- "$@" --model "$cfg_model"
      info "model: $cfg_model (from config)"
    fi
  fi
  if [[ $has_quant -eq 0 ]]; then
    local cfg_quant
    cfg_quant="$(config_get quant "")"
    if [[ -n "$cfg_quant" ]]; then
      set -- "$@" --quant "$cfg_quant"
    fi
  fi

  # Cache key: input + model + every pass-through flag + binary identity.
  local bin_stamp
  bin_stamp="$("$handy" --version 2>/dev/null | head -1)-$(wc -c <"$handy" 2>/dev/null | tr -d ' ')"
  local key
  key="$(cache_key "$input" "$bin_stamp" "$@")"
  local transcript_dir="$CACHE_DIR/transcripts"
  local cache_file="$transcript_dir/$key.txt"

  if [[ -f "$cache_file" && "${NO_CACHE:-0}" != "1" ]]; then
    info "cache hit: $cache_file"
    cat "$cache_file"
    return 0
  fi

  local tmp_output
  tmp_output="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f '$tmp_output'" EXIT

  if is_url "$input"; then
    need_cmd yt-dlp "Install it with: brew install yt-dlp  |  pipx install yt-dlp  |  scoop install yt-dlp"
    need_cmd ffmpeg "Install it with: brew install ffmpeg  |  apt install ffmpeg  |  scoop install ffmpeg"

    local tmpdir
    tmpdir="$(mktemp -d)"
    info "downloading audio: $input"
    if ! yt-dlp --no-update -x --audio-format m4a --audio-quality 0 \
      -o "$tmpdir/audio.%(ext)s" "$input" >&2; then
      rm -rf "$tmpdir"
      die "yt-dlp failed. If the site is blocked on your network, configure a proxy
  (export https_proxy=http://127.0.0.1:7890) or download the audio yourself and
  pass the local file instead."
    fi

    local audio
    audio="$(find "$tmpdir" -type f -name 'audio.*' | head -1)"
    if [[ -z "$audio" ]]; then
      rm -rf "$tmpdir"
      die "yt-dlp produced no audio file"
    fi

    local rc=0
    "$handy" "$audio" "$@" >"$tmp_output" || rc=$?
    rm -rf "$tmpdir"
    [[ $rc -eq 0 ]] || die "handy-transcribe exited with status $rc"
  else
    [[ -f "$input" ]] || die "input file not found: $input"
    local rc=0
    "$handy" "$input" "$@" >"$tmp_output" || rc=$?
    [[ $rc -eq 0 ]] || die "handy-transcribe exited with status $rc"
  fi

  mkdir -p "$transcript_dir"
  cp "$tmp_output" "$cache_file"
  {
    echo "input: $input"
    echo "options: $*"
    echo "binary: $handy"
    echo "created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"$cache_file.meta"

  cat "$cache_file"
}

main "$@"
