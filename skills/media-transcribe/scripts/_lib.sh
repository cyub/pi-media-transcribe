#!/usr/bin/env bash
# Shared helpers for the media-transcribe skill scripts.
# Sourced by transcribe.sh, to-obsidian.sh, and doctor.sh — not meant to be run.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$SKILL_DIR/scripts"

CONFIG_FILE="${MEDIA_TRANSCRIBE_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/pi-media-transcribe/config.json}"
CACHE_DIR="${MEDIA_TRANSCRIBE_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/pi-media-transcribe}"

info() { printf '%s\n' "$*" >&2; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

# need_cmd <command> <install hint>
need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "$1 not found. $2"
}

# resolve_python — prints python3 or python, whichever exists (Windows/Git Bash and some distros
# only ship `python`).
resolve_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s' "$candidate"
      return 0
    fi
  done
}

require_python() {
  local bin
  bin="$(resolve_python)"
  [[ -n "$bin" ]] || die "python3 not found. Install Python 3.9+:
    macOS:          brew install python@3.12
    Debian/Ubuntu:  sudo apt install python3
    Windows:        winget install Python.Python.3.12   (or run inside WSL)"
  printf '%s' "$bin"
}

# Resolved once; every helper below uses it so `python`-only systems work.
PYTHON="$(resolve_python)"
[[ -n "$PYTHON" ]] || PYTHON="python3"

# config_get <dotted.path> [default] — reads the JSON config, prints the value.
config_get() {
  local path="$1" default="${2-}"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    printf '%s' "$default"
    return 0
  fi
  "$PYTHON" - "$CONFIG_FILE" "$path" "$default" <<'PY'
import json, sys

cfg_path, dotted, default = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(cfg_path, encoding="utf-8") as fh:
        cur = json.load(fh)
except Exception:
    print(default, end="")
    raise SystemExit

for key in dotted.split("."):
    if isinstance(cur, dict) and key in cur:
        cur = cur[key]
    else:
        print(default, end="")
        raise SystemExit

if isinstance(cur, bool):
    print("true" if cur else "false", end="")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False), end="")
elif cur is None:
    print(default, end="")
else:
    print(cur, end="")
PY
}

# resolve_handy — prints the path of the handy-transcribe binary, or nothing.
resolve_handy() {
  local candidate
  if [[ -n "${HANDY_TRANSCRIBE_BIN:-}" && -x "${HANDY_TRANSCRIBE_BIN}" ]]; then
    printf '%s' "$HANDY_TRANSCRIBE_BIN"
    return 0
  fi
  candidate="$(config_get handyTranscribeBin "")"
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    printf '%s' "$candidate"
    return 0
  fi
  if candidate="$(command -v handy-transcribe 2>/dev/null)"; then
    printf '%s' "$candidate"
    return 0
  fi
  for candidate in \
    "$HOME/workspace/code/handy-cli/target/release/handy-transcribe" \
    "$HOME/.cargo/bin/handy-transcribe" \
    "/opt/homebrew/bin/handy-transcribe" \
    "/usr/local/bin/handy-transcribe"; do
    if [[ -x "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 0
}

require_handy() {
  local bin
  bin="$(resolve_handy)"
  if [[ -z "$bin" ]]; then
    die "handy-transcribe not found. Install it with:
    cargo install handy-transcribe        (or: cargo binstall handy-transcribe)
  or download a prebuilt binary: https://github.com/cyub/handy-transcribe/releases
  or point HANDY_TRANSCRIBE_BIN / handyTranscribeBin in $CONFIG_FILE at it."
  fi
  printf '%s' "$bin"
}

# cache_key <string...> — stable 32-char hash of the inputs.
cache_key() {
  "$PYTHON" - "$@" <<'PY'
import hashlib, sys

material = "\x00".join(sys.argv[1:])
print(hashlib.sha256(material.encode("utf-8")).hexdigest()[:32])
PY
}

is_url() {
  [[ "$1" == http://* || "$1" == https://* ]]
}

# youtube-ish detection, used for tagging notes.
looks_like_youtube() {
  case "$1" in
    *youtube.com/* | *youtu.be/* | *youtube-nocookie.com/*) return 0 ;;
    *) return 1 ;;
  esac
}
