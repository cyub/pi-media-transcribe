#!/usr/bin/env python3
"""Transcript -> Markdown note (optionally LLM-polished) filed into a notes folder.

Reads a raw transcript from stdin and writes a note. Two modes:

* default — an OpenAI-compatible LLM fixes ASR mistakes, segments the text, writes a
  summary, picks a destination folder and topic tags;
* ``--raw`` — no LLM at all: the transcript is written as-is under a frontmatter
  header. No API key, no token cost, no rewriting.

Long transcripts are handled with a map-reduce pass (compress each chunk, then merge)
so a multi-hour recording does not blow the model's context window.

Usage:
    llm_to_obsidian.py <source> [--vault PATH] [--base SUBDIR] [--locale auto|en|zh]
                                [--raw] [--overwrite] [--config PATH] [--print-vault]

Configuration (all keys optional), read from --config or
$MEDIA_TRANSCRIBE_CONFIG or ${XDG_CONFIG_HOME:-~/.config}/pi-media-transcribe/config.json:

    {
      "vault": "~/Documents/Obsidian Vault",
      "baseSubdir": "Notes",
      "locale": "auto",
      "tags": ["auto-transcribed"],
      "llm": {"baseUrl": "https://api.openai.com", "model": "gpt-5",
              "apiKeyEnv": "OPENAI_API_KEY",
              "maxDirectChars": 48000, "chunkChars": 24000},
      "frontmatter": {"createdField": "created_at", "modifiedField": "last_modify_at"},
      "headings": {"source": "Source", "summary": "Core ideas", "body": "Transcript"}
    }

Environment overrides: LLM_API_KEY, DEEPSEEK_API_KEY, LLM_BASE_URL, LLM_MODEL,
OBSIDIAN_VAULT, MEDIA_TRANSCRIBE_CONFIG.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(
    os.environ.get(
        "MEDIA_TRANSCRIBE_CONFIG",
        str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            / "pi-media-transcribe" / "config.json"),
    )
)

# Directories that should never receive a transcript note when picking folders.
SKIP_DIRS = {
    ".obsidian", ".trash", ".git", ".excalidraw", "node_modules",
    "templates", "模版", "模版文件夹", "copilot-custom-prompts", "textgenerator",
}

HEADINGS = {
    "en": {"source": "Source", "summary": "Core ideas", "body": "Transcript"},
    "zh": {"source": "来源", "summary": "核心内容", "body": "正文"},
    "ja": {"source": "出典", "summary": "要点", "body": "本文"},
    "ko": {"source": "출처", "summary": "핵심 내용", "body": "본문"},
    "ru": {"source": "Источник", "summary": "Ключевые идеи", "body": "Транскрипт"},
    "de": {"source": "Quelle", "summary": "Kernaussagen", "body": "Transkript"},
    "es": {"source": "Fuente", "summary": "Ideas clave", "body": "Transcripción"},
    "fr": {"source": "Source", "summary": "Idées clés", "body": "Transcription"},
    "pt": {"source": "Fonte", "summary": "Ideias principais", "body": "Transcrição"},
}

# Written scripts can be identified from character ranges alone. Latin-script languages cannot be
# told apart without a language model, so they fall back to English headings (the note body still
# follows the transcript's language).
SCRIPT_RANGES = [
    ("ja", r"[\u3040-\u309f\u30a0-\u30ff]"),  # hiragana / katakana
    ("ko", r"[\uac00-\ud7af\u1100-\u11ff]"),  # hangul
    ("zh", r"[\u4e00-\u9fff]"),                # CJK ideographs (checked after kana/hangul)
    ("ru", r"[\u0400-\u04ff]"),
    ("ar", r"[\u0600-\u06ff]"),
    ("el", r"[\u0370-\u03ff]"),
    ("he", r"[\u0590-\u05ff]"),
    ("th", r"[\u0e00-\u0e7f]"),
    ("hi", r"[\u0900-\u097f]"),
]

DEFAULT_TAGS = {
    "en": ["auto-transcribed"],
    "zh": ["自动转录"],
    "ja": ["自動文字起こし"],
    "ko": ["자동-전사"],
    "ru": ["автотранскрипция"],
    "de": ["auto-transkribiert"],
    "es": ["transcrito-automaticamente"],
    "fr": ["transcription-automatique"],
    "pt": ["transcrito-automaticamente"],
}

# Below this many characters the whole transcript goes to the model in one request.
DEFAULT_MAX_DIRECT_CHARS = 48_000
# Chunk size for the map-reduce pass.
DEFAULT_CHUNK_CHARS = 24_000

SYSTEM_PROMPT = """You are an expert transcript editor who files research notes into a notes vault.

You receive the raw speech-to-text transcript of one recording (video, podcast, talk, meeting),
plus the list of folders available in the destination vault.

Do these five things:

1. Proofread. Fix homophone mistakes, misheard proper nouns, broken technical terms and missing
   punctuation (ASR routinely turns "RAG" into "reg", "LLM" into "LM"/"L M", "HyDE" into "HIDE",
   and mangles names and numbers). Keep the speaker's claims, numbers and opinions exactly as
   spoken. Never invent facts, never add sections the speaker did not cover, never soften a
   conclusion.
2. Segment. Split the transcript into logical sections, each with a short `###` subheading, so the
   result reads like an article rather than a wall of text.
3. Summarize. Write a 150-300 word abstract of the whole recording.
4. Choose a folder. Pick exactly one entry from the provided folder list — the most specific folder
   that semantically fits. If nothing fits, return an empty string.
5. Tag and title. Choose 1-3 topic tags (lowercase, no spaces if avoidable) and a concise title
   without punctuation that is illegal in file names.

Write the title, abstract, subheadings and body in the same language as the transcript (Chinese
transcript -> Chinese note, English transcript -> English note). Never translate.

Output exactly one JSON object, nothing else, no markdown fences:

{"title":"...","directory":"...","tags":["..."],"summary":"...","body":"markdown body with ### subheadings, without frontmatter, without the title, without the summary"}"""

MAP_PROMPT = """You are compressing one part of a long speech-to-text transcript so that a later step can
write a single faithful article from all parts.

You receive part {index} of {total} of the transcript. Produce dense, faithful notes for this part:

- Keep every concrete fact: names, numbers, prices, dates, APIs, product and paper names,
  and the speaker's conclusions. Fix obvious ASR spelling errors, but never invent or generalize.
- Group the content under 2-6 `###` subheadings, in the order it was spoken.
- Under each subheading use short bullet points. Add a `> ` quote line when a sentence is
  the speaker's own crisp formulation of a key claim.
- Write a 3-5 sentence summary of this part only.

Write in the same language as the transcript. Output exactly one JSON object:
{"summary":"3-5 sentences","notes":"markdown with ### subheadings and bullets"}"""

REDUCE_PROMPT = """You are assembling one article from compressed notes that cover consecutive parts of a
single recording. The parts arrive in order.

Produce the final note:

1. Merge the parts into one coherent article: keep all `###` sections in order, drop duplicated
   subheadings, and smooth transitions. Do not drop facts, numbers or names.
2. Write a 150-300 word abstract of the whole recording.
3. Choose one folder from the provided folder list (the most specific fit; empty string if none).
4. Choose 1-3 topic tags and a concise title without illegal file-name punctuation.

Write in the same language as the notes. Output exactly one JSON object, nothing else:
{"title":"...","directory":"...","tags":["..."],"summary":"...","body":"markdown body with ### subheadings"}"""


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - a broken config must not be fatal
        print(f"warning: ignoring unreadable config {path}: {exc}", file=sys.stderr)
        return {}


def config_path_for(args: argparse.Namespace) -> Path:
    return Path(args.config).expanduser() if args.config else DEFAULT_CONFIG_PATH


def detect_vault(config: dict) -> Path | None:
    """--vault / $OBSIDIAN_VAULT / config, then Obsidian's own vault registry."""
    env_vault = os.environ.get("OBSIDIAN_VAULT")
    for candidate in (env_vault, config.get("vault")):
        if candidate:
            path = Path(str(candidate)).expanduser()
            if path.is_dir():
                return path
            print(f"warning: notes folder not found: {path}", file=sys.stderr)

    if os.name == "nt":
        registry_dirs = [Path(os.environ.get("APPDATA", "")) / "obsidian"]
    elif sys.platform == "darwin":
        registry_dirs = [Path.home() / "Library" / "Application Support" / "obsidian"]
    else:
        registry_dirs = [
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "obsidian",
            Path.home() / ".var" / "app" / "md.obsidian.Obsidian" / "config" / "obsidian",
        ]

    for registry in registry_dirs:
        registry_file = registry / "obsidian.json"
        if not registry_file.is_file():
            continue
        try:
            data = json.loads(registry_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        vaults = data.get("vaults") or {}
        entries = sorted(
            vaults.values(),
            key=lambda v: (bool(v.get("open")), float(v.get("ts") or 0)),
            reverse=True,
        )
        for entry in entries:
            path = Path(str(entry.get("path", ""))).expanduser()
            if path.is_dir():
                return path

    default = Path.home() / "Documents" / "Obsidian Vault"
    return default if default.is_dir() else None


# Endpoints we know by name. A key is only ever sent to the endpoint of the provider it belongs to.
PROVIDER_ENDPOINTS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com",
    "openrouter": "https://openrouter.ai/api",
}
# Only providers with a model name we are confident about get a default; everything else must be
# configured explicitly rather than guessing a model that may not exist.
PROVIDER_DEFAULT_MODELS = {"deepseek": "deepseek-chat"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower()


def provider_of(base_url: str) -> str | None:
    """Which provider an endpoint belongs to, if it is one we know."""
    host = _host(base_url)
    for provider, endpoint in PROVIDER_ENDPOINTS.items():
        if host and host == _host(endpoint):
            return provider
    return None


def is_local_endpoint(base_url: str) -> bool:
    return _host(base_url) in LOCAL_HOSTS


def key_from_pi_auth(provider: str | None) -> str | None:
    """Read a key for *this provider* from Pi's auth.json.

    Only the matching provider's key is ever returned: handing one provider's credential to another
    provider's endpoint would disclose it to an unrelated service.
    """
    if not provider:
        return None
    auth = Path.home() / ".pi" / "agent" / "auth.json"
    if not auth.is_file():
        return None
    try:
        data = json.loads(auth.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    entry = data.get(provider) or {}
    key = entry.get("key") if isinstance(entry, dict) else None
    return key.strip() if isinstance(key, str) and key.strip() else None


def resolve_llm(config: dict) -> tuple[str | None, str, str, int, int, str]:
    """Resolve endpoint, model and key, keeping key and endpoint in the same provider.

    Order for the endpoint: `$LLM_BASE_URL` -> `llm.baseUrl` -> the endpoint of `llm.provider`
    (default DeepSeek). The key then comes from a source that belongs to that endpoint, and only
    from that one: `$LLM_API_KEY`, `$<PROVIDER>_API_KEY`, the variable named by `llm.apiKeyEnv`,
    a placeholder for a local server, or Pi's stored credential *for the same provider*.

    Returns (key, base_url, model, max_direct_chars, chunk_chars, key_source).
    """
    llm = config.get("llm") or {}
    configured_provider = str(llm.get("provider") or "").strip().lower() or None

    base_url = (os.environ.get("LLM_BASE_URL") or llm.get("baseUrl") or "").rstrip("/")
    if not base_url:
        base_url = PROVIDER_ENDPOINTS.get(configured_provider or "deepseek", PROVIDER_ENDPOINTS["deepseek"])
    provider = provider_of(base_url) or configured_provider

    model = os.environ.get("LLM_MODEL") or llm.get("model") or ""
    if not model:
        model = PROVIDER_DEFAULT_MODELS.get(provider or "", "")

    api_key: str | None = None
    source = ""
    if os.environ.get("LLM_API_KEY"):
        api_key, source = os.environ["LLM_API_KEY"], "LLM_API_KEY"
    if not api_key and provider:
        env_name = f"{provider.upper()}_API_KEY"
        if os.environ.get(env_name):
            api_key, source = os.environ[env_name], env_name
    if not api_key:
        env_name = str(llm.get("apiKeyEnv") or "")
        if env_name and os.environ.get(env_name):
            api_key, source = os.environ[env_name], env_name
            implied = env_name.replace("_API_KEY", "").replace("_KEY", "").lower()
            if provider and implied in PROVIDER_ENDPOINTS and implied != provider:
                print(
                    f"warning: llm.apiKeyEnv is {env_name} but the endpoint is {base_url} "
                    f"({provider}); that key will be sent to {provider}. Set llm.baseUrl or "
                    f"llm.provider to match.",
                    file=sys.stderr,
                )
    if not api_key and is_local_endpoint(base_url):
        # Local servers (Ollama, LM Studio, vLLM) ignore the key, so a placeholder is enough.
        api_key, source = "local", "no key needed for a local endpoint"
    if not api_key and provider:
        api_key = key_from_pi_auth(provider)
        if api_key:
            source = f"~/.pi/agent/auth.json ({provider})"

    max_direct = int(llm.get("maxDirectChars") or DEFAULT_MAX_DIRECT_CHARS)
    chunk_chars = int(llm.get("chunkChars") or DEFAULT_CHUNK_CHARS)
    return api_key, base_url, model, max_direct, chunk_chars, source


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def detect_locale(transcript: str, pinned: str) -> str:
    """Pick the note's heading language: explicit pin, else the dominant written script, else English."""
    if pinned and pinned != "auto":
        return pinned if pinned in HEADINGS else "en"

    counts = []
    for code, pattern in SCRIPT_RANGES:
        matches = len(re.findall(pattern, transcript))
        if matches:
            counts.append((matches, code))
    if not counts:
        return "en"

    best_count, best_code = max(counts)
    # A handful of stray glyphs should not switch the whole note's language, and scripts without a
    # heading preset (Arabic, Hebrew, Greek, Thai, Devanagari, …) fall back to English labels while
    # the body still follows the transcript's language.
    if best_code not in HEADINGS:
        return "en"
    letters = len(re.findall(r"\w", transcript, re.UNICODE)) or len(transcript) or 1
    return best_code if (best_count >= 20 or best_count / letters >= 0.05) else "en"


def list_folders(vault: Path, base: str) -> list[str]:
    """Up to two levels of subfolders, relative to the vault root."""
    root = (vault / base) if base else vault
    if not root.is_dir():
        return []
    folders: list[str] = []
    if base:
        # Offer the base folder itself, so a base with no subfolders is still a valid choice.
        folders.append(root.relative_to(vault).as_posix())
    for first in sorted(root.iterdir()):
        if not first.is_dir() or first.name.startswith(".") or first.name.lower() in SKIP_DIRS:
            continue
        folders.append(first.relative_to(vault).as_posix())
        for second in sorted(first.iterdir()):
            if not second.is_dir() or second.name.startswith(".") or second.name.lower() in SKIP_DIRS:
                continue
            folders.append(second.relative_to(vault).as_posix())
    return folders


def post_chat(api_key: str, base_url: str, model: str, messages: list[dict],
              attempt: int = 1) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        if exc.code in (429, 500, 502, 503, 504) and attempt == 1:
            print(f"warning: LLM returned HTTP {exc.code}, retrying once…", file=sys.stderr)
            time.sleep(3)
            return post_chat(api_key, base_url, model, messages, attempt=2)
        hint = {
            401: "check your API key (LLM_API_KEY / llm.apiKeyEnv)",
            404: "check llm.baseUrl — it should be the API root, without /v1/chat/completions",
            402: "the account is out of credit",
            413: "the request is too large — lower llm.maxDirectChars / llm.chunkChars",
        }.get(exc.code, "")
        raise SystemExit(f"error: LLM call failed (HTTP {exc.code}){f' — {hint}' if hint else ''}: {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"error: cannot reach the LLM endpoint {base_url}: {exc.reason}")
    return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise SystemExit("error: the LLM response did not contain a JSON object")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: could not parse the LLM JSON: {exc}")


def safe_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "untitled"


def default_title(source: str) -> str:
    """A filename-safe title derived from the source, for --raw notes."""
    if re.match(r"^https?://", source):
        parsed = urllib.parse.urlparse(source)
        host = parsed.netloc.replace("www.", "")
        tail = parsed.path.rstrip("/").split("/")[-1]
        tail = " ".join(filter(None, [parsed.query.split("&")[0].split("=")[-1], tail]))
        return safe_filename(f"{host} {tail}".strip())
    return safe_filename(Path(source).stem)


def split_transcript(text: str, chunk_chars: int) -> list[str]:
    """Split on paragraph boundaries near `chunk_chars`, never mid-paragraph if avoidable."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in paragraphs:
        if len(paragraph) > chunk_chars:
            # Hard-split an oversized paragraph on sentence ends.
            sentences = re.split(r"(?<=[。！？.!?])\s*", paragraph)
            for sentence in sentences:
                if size + len(sentence) > chunk_chars and current:
                    chunks.append("\n\n".join(current))
                    current, size = [], 0
                current.append(sentence)
                size += len(sentence)
            continue
        if size + len(paragraph) > chunk_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(paragraph)
        size += len(paragraph)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def unique_path(directory: Path, stem: str, overwrite: bool) -> Path:
    path = directory / f"{stem}.md"
    if overwrite or not path.exists():
        return path
    for index in range(2, 100):
        candidate = directory / f"{stem} {index}.md"
        if not candidate.exists():
            return candidate
    raise SystemExit(f"error: too many notes named {stem!r} in {directory}")


def note_tags(result: dict, locale: str, config: dict, is_youtube: bool) -> list[str]:
    extra_tags = config.get("tags")
    if extra_tags is None:
        extra_tags = DEFAULT_TAGS.get(locale, DEFAULT_TAGS["en"])
    tags: list[str] = []
    if is_youtube:
        tags.append("youtube")
    for tag in list(extra_tags) + list(result.get("tags") or []):
        tag = str(tag).strip().lstrip("#")
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def frontmatter(tags: list[str], config: dict) -> str:
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    meta = config.get("frontmatter") or {}
    created_field = meta.get("createdField", "created_at")
    modified_field = meta.get("modifiedField", "last_modify_at")
    tag_block = "\n".join(f"  - {tag}" for tag in tags) if tags else "  - note"
    return (
        "---\n"
        f"{created_field}: {now}\n"
        f"{modified_field}: {now}\n"
        "tags:\n"
        f"{tag_block}\n"
        "---\n"
    )


def build_note(result: dict, source: str, locale: str, config: dict, is_youtube: bool) -> str:
    headings = dict(HEADINGS[locale])
    headings.update(config.get("headings") or {})
    body = str(result.get("body") or "").strip()
    for prefix in ("## " + headings["body"], headings["body"]):
        if body.startswith(prefix):
            body = body[len(prefix) :].lstrip("\n")
            break
    source_sep = "：" if locale in ("zh", "ja") else ": "
    return (
        frontmatter(note_tags(result, locale, config, is_youtube), config)
        + f"{headings['source']}{source_sep}{source}\n\n"
        f"## {headings['summary']}\n"
        f"{str(result.get('summary') or '').strip()}\n\n"
        "---\n\n"
        f"## {headings['body']}\n"
        f"{body}\n"
    )


def build_raw_note(transcript: str, source: str, title: str, locale: str,
                   config: dict, is_youtube: bool) -> str:
    """No-LLM note: frontmatter, a title, and the transcript verbatim."""
    headings = dict(HEADINGS[locale])
    headings.update(config.get("headings") or {})
    source_sep = "：" if locale in ("zh", "ja") else ": "
    tags = note_tags({"tags": []}, locale, config, is_youtube)
    return (
        frontmatter(tags, config)
        + f"{headings['source']}{source_sep}{source}\n\n"
        f"# {title}\n\n"
        f"{transcript.strip()}\n"
    )


# --------------------------------------------------------------------------- #
# LLM pipeline
# --------------------------------------------------------------------------- #
def run_single_pass(api_key: str, base_url: str, model: str, transcript: str,
                    source: str, folders: list[str]) -> dict:
    user = (
        f"Source: {source}\n\n"
        f"Transcript:\n{transcript}\n\n"
        f"Folders available in the vault (relative to the vault root):\n"
        + ("\n".join(f"- {f}" for f in folders) if folders else "(no folders — leave directory empty)")
    )
    raw = post_chat(api_key, base_url, model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ])
    return extract_json(raw)


def run_map_reduce(api_key: str, base_url: str, model: str, transcript: str,
                   source: str, folders: list[str], chunk_chars: int) -> dict:
    chunks = split_transcript(transcript, chunk_chars)
    total = len(chunks)
    print(f"long transcript: {len(transcript):,} chars -> {total} chunks (map-reduce)", file=sys.stderr)

    digests: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        print(f"  compressing chunk {index}/{total} ({len(chunk):,} chars)…", file=sys.stderr)
        raw = post_chat(api_key, base_url, model, [
            {"role": "system", "content": MAP_PROMPT.replace("{index}", str(index)).replace("{total}", str(total))},
            {"role": "user", "content": chunk},
        ])
        part = extract_json(raw)
        digests.append(
            f"### Part {index}/{total} — summary\n{str(part.get('summary') or '').strip()}\n\n"
            f"{str(part.get('notes') or '').strip()}"
        )

    user = (
        f"Source: {source}\n\n"
        "Compressed notes for each part of the recording, in order:\n\n"
        + "\n\n---\n\n".join(digests)
        + "\n\nFolders available in the vault (relative to the vault root):\n"
        + ("\n".join(f"- {f}" for f in folders) if folders else "(no folders — leave directory empty)")
    )
    print("  merging parts into one note…", file=sys.stderr)
    raw = post_chat(api_key, base_url, model, [
        {"role": "system", "content": REDUCE_PROMPT},
        {"role": "user", "content": user},
    ])
    return extract_json(raw)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn a raw transcript (stdin) into a Markdown note.",
    )
    parser.add_argument("source", nargs="?",
                        help="URL or file path the transcript came from")
    parser.add_argument("--vault", help="notes folder (Obsidian vault or any directory)")
    parser.add_argument("--base", help="subfolder of the notes folder to file notes under")
    parser.add_argument("--locale", default=None,
                        help="heading language for the note: auto (default), en, zh, ja, ko, ru, de, "
                             "es, fr, pt — anything else falls back to English")
    parser.add_argument("--title", help="note title to use instead of deriving one from <source>")
    parser.add_argument("--raw", action="store_true",
                        help="skip the LLM entirely: write the transcript verbatim (no API key needed)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing note with the same title")
    parser.add_argument("--config", help="path to config.json")
    parser.add_argument("--print-vault", action="store_true", help="print the resolved folder and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(config_path_for(args))

    vault = Path(args.vault).expanduser() if args.vault else detect_vault(config)
    # Resolve once so `relative_to` below is not defeated by /tmp -> /private/tmp symlinks.
    if vault is not None:
        vault = vault.resolve()
    if args.print_vault:
        print(vault if vault else "")
        return
    if vault is None or not vault.is_dir():
        raise SystemExit(
            "error: no notes folder found. Pass --vault PATH, set OBSIDIAN_VAULT, "
            f"or add \"vault\" to {config_path_for(args)}"
        )

    base = args.base if args.base is not None else str(config.get("baseSubdir") or "")
    pinned = args.locale or str(config.get("locale") or "auto")

    transcript = sys.stdin.read().strip()
    if not args.source:
        raise SystemExit("error: missing <source> (the URL or file path the transcript came from)")
    if not transcript:
        raise SystemExit("error: empty transcript on stdin")

    locale = detect_locale(transcript, pinned)
    is_youtube = bool(re.search(r"(youtube\.com|youtu\.be|youtube-nocookie\.com)", args.source))
    folders = list_folders(vault, base)

    if args.raw:
        title = safe_filename(args.title) if args.title else default_title(args.source)
        directory = base
        note = build_raw_note(transcript, args.source, title, locale, config, is_youtube)
        print(f"raw mode: no LLM, {len(transcript):,} chars kept verbatim", file=sys.stderr)
    else:
        api_key, base_url, model, max_direct, chunk_chars, key_source = resolve_llm(config)
        if not api_key:
            provider = provider_of(base_url) or "the endpoint's provider"
            raise SystemExit(
                f"error: no LLM API key for {base_url}. Set LLM_API_KEY, or the variable named by "
                f"llm.apiKeyEnv, or store a {provider} key for that same provider (run /login in Pi "
                f"for DeepSeek), or use --raw to skip the LLM. A key is never taken from another "
                f"provider, because that would send it to a service it does not belong to."
            )
        if not model:
            raise SystemExit(
                f"error: no model configured for {base_url}. Set llm.model (for example "
                f"\"gpt-5-mini\" for OpenAI or \"qwen3:8b\" for a local Ollama server)."
            )
        print(f"LLM: {model} via {base_url} (key: {key_source}; note language: {locale}, "
              f"{len(folders)} folders offered)", file=sys.stderr)
        if len(transcript) <= max_direct:
            result = run_single_pass(api_key, base_url, model, transcript, args.source, folders)
        else:
            result = run_map_reduce(api_key, base_url, model, transcript, args.source, folders,
                                    chunk_chars)
        title = safe_filename(str(result.get("title") or "untitled"))
        directory = str(result.get("directory") or "").strip().strip("/")
        if not directory:
            # The model found no fitting folder; fall back to the configured base instead of the root.
            directory = base
        note = build_note(result, args.source, locale, config, is_youtube)

    dest_dir = (vault / directory).resolve() if directory else vault.resolve()
    if not str(dest_dir).startswith(str(vault.resolve())):
        print(f"warning: folder outside the notes folder ({directory}) — filing at the root", file=sys.stderr)
        dest_dir = vault.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = unique_path(dest_dir, title, args.overwrite)
    dest.write_text(note, encoding="utf-8")

    rel = dest.relative_to(vault)
    print(f"已保存 / saved: {dest}" if locale == "zh" else f"saved: {dest}", file=sys.stderr)
    print(rel.as_posix())


if __name__ == "__main__":
    main()
