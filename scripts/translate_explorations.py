#!/usr/bin/env python3
"""Translate English explorations into a target locale directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "scripts" / "translation" / "config.yaml"
ENV_FALLBACK = ROOT.parent / "threads-of-meaning" / ".env"

SYSTEM_PROMPT = """You are a literary translator for blog essays from the Weaver's Town website.

Translate the provided Markdown from English to {target_language} ({target_locale}).

Rules:
1. Return ONLY the translated Markdown. No commentary, no code fences.
2. Preserve ALL Markdown syntax exactly: headings, lists, bold, italic, links, images, blockquotes.
3. Do NOT translate or alter protected placeholders like <<PROTECTED_0>>.
4. Keep Hugo shortcodes, image paths, and /images/ URLs unchanged.
5. Keep HTML tags unchanged.
6. Keep author name "Arman Fatahi" unchanged.
7. Use natural, literary {target_language} suitable for publication.
8. Apply this glossary consistently (English → {target_language}):
{glossary}
"""


@dataclass
class ProviderConfig:
    name: str
    base_url: str | None
    api_key_env: str
    default_model: str


@dataclass
class Config:
    source_dir: Path
    target_dir: Path
    state_file: Path
    glossary: dict[str, str]
    static_translations: dict[str, str]
    frontmatter_translate_keys: list[str]
    frontmatter_preserve_keys: list[str]
    target_language: str
    target_locale: str
    provider: ProviderConfig
    model: str


def load_dotenv() -> None:
    for env_path in (ROOT / ".env", ENV_FALLBACK):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def load_config(config_path: Path) -> Config:
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    providers_raw = raw.get("providers", {})
    provider_name = resolve_provider_name(providers_raw)
    provider_settings = providers_raw[provider_name]
    provider = ProviderConfig(
        name=provider_name,
        base_url=provider_settings.get("base_url"),
        api_key_env=provider_settings["api_key_env"],
        default_model=provider_settings["default_model"],
    )

    return Config(
        source_dir=ROOT / raw["source_dir"],
        target_dir=ROOT / raw["target_dir"],
        state_file=ROOT / raw["state_file"],
        glossary=raw.get("glossary", {}),
        static_translations=raw.get("static_translations", {}),
        frontmatter_translate_keys=raw.get("frontmatter_translate_keys", []),
        frontmatter_preserve_keys=raw.get("frontmatter_preserve_keys", []),
        target_language=raw.get("target_language", "Vietnamese"),
        target_locale=raw.get("target_locale", "vi-VN"),
        provider=provider,
        model=os.environ.get("TRANSLATION_MODEL", provider.default_model),
    )


def resolve_provider_name(providers_raw: dict[str, Any]) -> str:
    explicit = os.environ.get("TRANSLATION_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    for name in ("xai", "openai"):
        settings = providers_raw.get(name, {})
        env_name = settings.get("api_key_env", "")
        if env_name and os.environ.get(env_name, "").strip():
            return name
    return "xai"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"files": {}}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def split_front_matter(text: str) -> tuple[str, dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return "", {}, text
    front_matter = match.group(0)
    meta = yaml.safe_load(front_matter.removeprefix("---\n").removesuffix("---\n")) or {}
    return front_matter, meta, text[match.end() :]


class Protector:
    def __init__(self) -> None:
        self.tokens: dict[str, str] = {}
        self.counter = 0

    def _add(self, match: re.Match[str]) -> str:
        key = f"<<PROTECTED_{self.counter}>>"
        self.counter += 1
        self.tokens[key] = match.group(0)
        return key

    def protect(self, text: str) -> str:
        patterns = [
            r"\{\{<[^>]+\}\}\}",
            r"\{\{[^}]+\}\}",
            r"\[@(?:[^\]]+)\]",
            r"!\[[^\]]*\]\([^)]+\)",
            r"\[[^\]]+\]\([^)]+\)",
            r"<[^>]+>",
            r"https?://[^\s)>]+",
            r"`[^`]+`",
        ]
        protected = text
        for pattern in patterns:
            protected = re.sub(pattern, self._add, protected)
        return protected

    def restore(self, text: str) -> str:
        restored = text
        for token, original in self.tokens.items():
            restored = restored.replace(token, original)
        return restored


def glossary_prompt(config: Config) -> str:
    return "\n".join(f'- "{en}" → "{translated}"' for en, translated in config.glossary.items())


def system_prompt(config: Config) -> str:
    return SYSTEM_PROMPT.format(
        target_language=config.target_language,
        target_locale=config.target_locale,
        glossary=glossary_prompt(config),
    )


def chunk_markdown(text: str, max_chars: int = 7000) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    chunks: list[str] = []
    current = ""

    for part in parts:
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current += part
            continue
        if current.strip():
            chunks.append(current)
        if len(part) <= max_chars:
            current = part
            continue

        paragraphs = part.split("\n\n")
        current = ""
        for paragraph in paragraphs:
            block = paragraph if not current else current + "\n\n" + paragraph
            if len(block) <= max_chars:
                current = block
            else:
                if current.strip():
                    chunks.append(current)
                current = paragraph
        if current.strip():
            chunks.append(current)
            current = ""

    if current.strip():
        chunks.append(current)

    return chunks or [text]


def translate_text(text: str, config: Config, client: Any) -> str:
    protector = Protector()
    protected = protector.protect(text)
    translated_chunks: list[str] = []
    for chunk in chunk_markdown(protected):
        response = client.chat.completions.create(
            model=config.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt(config)},
                {"role": "user", "content": f"Translate this Markdown to {config.target_language}.\n\n{chunk}"},
            ],
        )
        translated = (response.choices[0].message.content or "").strip()
        if translated.startswith("```"):
            translated = re.sub(r"^```[a-z]*\n?", "", translated)
            translated = re.sub(r"\n?```$", "", translated)
        translated_chunks.append(translated)
    return protector.restore("\n\n".join(translated_chunks))


def field_hint(field: str, config: Config) -> str:
    language = config.target_language
    hints = {
        "title": f"Translate this article title to {language}.",
        "summary": f"Translate this article summary to {language}. Keep it one paragraph.",
        "description": f"Translate this section description to {language}.",
        "audio_title": f"Translate this short website UI label to {language}.",
    }
    return hints.get(field, f"Translate this website metadata to {language}.")


def translate_scalar(field: str, value: str, config: Config, client: Any) -> str:
    if value in config.static_translations:
        return config.static_translations[value]

    hint = field_hint(field, config)
    response = client.chat.completions.create(
        model=config.model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You translate website metadata strings from English to {config.target_language}. "
                    f"Return only the translated {config.target_language} text. No quotes, no commentary, "
                    "no refusals.\n"
                    f"{hint}\n"
                    f"{glossary_prompt(config)}"
                ),
            },
            {"role": "user", "content": value},
        ],
    )
    translated = (response.choices[0].message.content or "").strip()
    translated = re.sub(r"^```[a-z]*\n?|```$", "", translated).strip()
    translated = translated.strip('"').strip("'")
    if field in {"title", "audio_title"}:
        return translated.splitlines()[0].strip()
    return translated


def extract_h1(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def render_front_matter(meta: dict[str, Any]) -> str:
    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{dumped}\n---\n"


def discover_files(source_dir: Path) -> list[Path]:
    return sorted(source_dir.glob("*.md"))


def build_client(config: Config) -> Any:
    api_key = os.environ.get(config.provider.api_key_env, "").strip()
    if not api_key:
        print(f"Error: {config.provider.api_key_env} is not set.", file=sys.stderr)
        sys.exit(1)
    from openai import OpenAI

    kwargs: dict[str, Any] = {"api_key": api_key}
    if config.provider.base_url:
        kwargs["base_url"] = config.provider.base_url
    print(f"Using provider: {config.provider.name} ({config.model})")
    return OpenAI(**kwargs)


def translate_file(source_path: Path, config: Config, client: Any, state: dict[str, Any], force: bool) -> bool:
    rel = source_path.name
    target_path = config.target_dir / rel
    source_hash = sha256_file(source_path)
    previous = state.get("files", {}).get(rel, {})

    if not force and previous.get("source_sha256") == source_hash and target_path.exists():
        print(f"skip {rel} (unchanged)")
        return False

    print(f"translate {rel}")
    raw = source_path.read_text(encoding="utf-8")
    _, meta, body = split_front_matter(raw)

    translated_meta = {key: meta[key] for key in config.frontmatter_preserve_keys if key in meta}
    translated_body = translate_text(body, config, client)

    h1_title = extract_h1(translated_body)
    if h1_title:
        translated_meta["title"] = h1_title

    for key in config.frontmatter_translate_keys:
        if key == "title":
            continue
        if key not in meta or not isinstance(meta[key], str):
            continue
        if key == "audio_title":
            translated_meta[key] = config.static_translations.get(
                meta[key],
                config.static_translations.get("Listen to this article", meta.get(key, "")),
            )
            continue
        translated_meta[key] = translate_scalar(key, meta[key], config, client)
        time.sleep(0.3)
    output = render_front_matter(translated_meta) + "\n" + translated_body.lstrip("\n")
    config.target_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(output, encoding="utf-8")

    state.setdefault("files", {})[rel] = {
        "source_sha256": source_hash,
        "translated_at": datetime.now(timezone.utc).isoformat(),
        "provider": config.provider.name,
        "model": config.model,
    }
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to translation config YAML (default: scripts/translation/config.yaml)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--file", help="Translate one exploration filename, e.g. _index.md")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = load_config(config_path)
    state = load_state(config.state_file)
    files = discover_files(config.source_dir)
    if args.file:
        files = [config.source_dir / args.file]

    if args.dry_run:
        for path in files:
            rel = path.name
            previous = state.get("files", {}).get(rel, {})
            status = "stale" if previous.get("source_sha256") != sha256_file(path) else "current"
            print(f"{status}: {rel}")
        return

    client = build_client(config)
    changed = 0
    for source_path in files:
        if translate_file(source_path, config, client, state, args.force):
            changed += 1
            time.sleep(0.5)

    save_state(config.state_file, state)
    print(f"Done. Updated {changed} exploration file(s).")


if __name__ == "__main__":
    main()