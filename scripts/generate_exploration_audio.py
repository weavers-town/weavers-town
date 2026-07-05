#!/usr/bin/env python3
"""Generate exploration MP3 audio for the website using xAI Text-to-Speech."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "scripts" / "audio" / "config.yaml"
FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


@dataclass
class LocaleConfig:
    name: str
    content_dir: Path
    language: str
    output_dir: Path
    audio_path_prefix: str
    spoken_label: str
    audio_title: str


@dataclass
class Config:
    api_url: str
    api_key_env: str
    state_file: Path
    voice_id: str
    speed: float
    max_chunk_chars: int
    output_format: dict[str, Any]
    audio_names: dict[str, str]
    locales: dict[str, LocaleConfig]


def load_dotenv() -> None:
    for env_path in (ROOT / ".env", ROOT.parent / "threads-of-meaning" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config() -> Config:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    locales: dict[str, LocaleConfig] = {}
    for name, settings in raw["locales"].items():
        locales[name] = LocaleConfig(
            name=name,
            content_dir=ROOT / settings["content_dir"],
            language=settings["language"],
            output_dir=ROOT / settings["output_dir"],
            audio_path_prefix=settings.get("audio_path_prefix", ""),
            spoken_label=settings["spoken_label"],
            audio_title=settings["audio_title"],
        )

    return Config(
        api_url=raw["api_url"],
        api_key_env=raw["api_key_env"],
        state_file=ROOT / raw["state_file"],
        voice_id=raw.get("voice_id", "leo"),
        speed=float(raw.get("speed", 1.0)),
        max_chunk_chars=int(raw.get("max_chunk_chars", 6000)),
        output_format=raw.get("output_format", {"codec": "mp3", "sample_rate": 24000, "bit_rate": 128000}),
        audio_names=raw.get("audio_names", {}),
        locales=locales,
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def split_front_matter(text: str) -> tuple[str, dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return "", {}, text
    front_matter = match.group(0)
    meta = yaml.safe_load(front_matter.removeprefix("---\n").removesuffix("---\n")) or {}
    return front_matter, meta, text[match.end() :]


def extract_title(path: Path, meta: dict[str, Any]) -> str:
    title = meta.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def resolve_audio_name(path: Path, meta: dict[str, Any], config: Config) -> str:
    audio_value = meta.get("audio")
    if isinstance(audio_value, str) and audio_value.strip():
        cleaned = audio_value.strip().strip('"').strip("'")
        cleaned = cleaned.removeprefix("audio/").removeprefix("vi/").removeprefix("fa/")
        return Path(cleaned).stem
    if path.stem in config.audio_names:
        return config.audio_names[path.stem]
    return path.stem


def audio_frontmatter_value(locale: LocaleConfig, audio_name: str) -> str:
    return f"{locale.audio_path_prefix}{audio_name}.mp3"


def update_frontmatter(path: Path, audio: str, audio_title: str) -> bool:
    text = path.read_text(encoding="utf-8")
    _, meta, body = split_front_matter(text)
    if not meta:
        return False

    changed = False
    if meta.get("audio") != audio:
        meta["audio"] = audio
        changed = True
    if meta.get("audio_title") != audio_title:
        meta["audio_title"] = audio_title
        changed = True
    if not changed:
        return False

    dumped = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    path.write_text(f"---\n{dumped}\n---\n{body}", encoding="utf-8")
    return True


def markdown_to_plain_text(source_file: Path) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        temp_path = Path(tmp.name)

    try:
        if shutil.which("pandoc"):
            subprocess.run(
                [
                    "pandoc",
                    str(source_file),
                    "--to=plain",
                    "--wrap=none",
                    "--strip-comments",
                    "-o",
                    str(temp_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            temp_path.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")

        text = temp_path.read_text(encoding="utf-8")
    finally:
        temp_path.unlink(missing_ok=True)

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        line = re.sub(r"\*\*\*?([^*]+)\*\*\*?", r"\1", line)
        line = re.sub(r"\[\^[^\]]*\]", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[@?[^\]]*\]", "", line)
        line = re.sub(r"\{[^}]*\}", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned_lines.append(line)

    return "\n\n".join(cleaned_lines).strip()


def build_spoken_text(locale: LocaleConfig, source_file: Path, meta: dict[str, Any]) -> str:
    title = extract_title(source_file, meta)
    body = markdown_to_plain_text(source_file)
    return f"{locale.spoken_label}: {title}.\n\n{body}\n\nEnd of {locale.spoken_label}."


def chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current.strip():
            chunks.append(current.strip())
        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        current = ""
        for sentence in sentences:
            block = sentence if not current else f"{current} {sentence}"
            if len(block) <= max_chars:
                current = block
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = sentence
        if current.strip():
            chunks.append(current.strip())
            current = ""

    if current.strip():
        chunks.append(current.strip())

    return chunks or [text]


def synthesize_chunk(text: str, config: Config, api_key: str, language: str) -> bytes:
    payload = {
        "text": text,
        "voice_id": config.voice_id,
        "language": language,
        "speed": config.speed,
        "output_format": config.output_format,
    }
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                config.api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=(30, 900),
            )
            if response.status_code >= 400:
                raise RuntimeError(f"xAI TTS failed ({response.status_code}): {response.text[:500]}")
            return response.content
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as exc:
            last_error = exc
            if attempt < 3:
                wait_seconds = attempt * 10
                print(f"  retry chunk ({attempt}/3) after network error: {exc}")
                time.sleep(wait_seconds)
            else:
                raise
    raise RuntimeError(f"xAI TTS failed after retries: {last_error}")


def concat_mp3_files(chunk_files: list[Path], output_file: Path) -> None:
    if len(chunk_files) == 1:
        shutil.copyfile(chunk_files[0], output_file)
        return

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to concatenate exploration audio chunks.")

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        concat_list = Path(handle.name)
        for chunk_file in chunk_files:
            handle.write(f"file '{chunk_file.resolve()}'\n")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(output_file),
                "-y",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffmpeg concat failed")
    finally:
        concat_list.unlink(missing_ok=True)


def discover_explorations(locale: LocaleConfig) -> list[Path]:
    if not locale.content_dir.exists():
        return []
    explorations: list[Path] = []
    for path in sorted(locale.content_dir.glob("*.md")):
        if path.name == "_index.md":
            continue
        _, meta, _ = split_front_matter(path.read_text(encoding="utf-8"))
        if meta.get("draft"):
            continue
        explorations.append(path)
    return explorations


def record_state_entry(
    state: dict[str, Any],
    state_key: str,
    source_file: Path,
    output_file: Path,
    source_hash: str,
    *,
    chunks: int | None = None,
    chars: int | None = None,
    language: str,
    bootstrapped: bool = False,
) -> None:
    entry: dict[str, Any] = {
        "source_sha256": source_hash,
        "source": str(source_file.relative_to(ROOT)),
        "output": str(output_file.relative_to(ROOT)),
        "language": language,
    }
    if chunks is not None:
        entry["chunks"] = chunks
    if chars is not None:
        entry["chars"] = chars
    if bootstrapped:
        entry["bootstrapped"] = True
    else:
        entry["voice_id"] = "leo"
        entry["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state.setdefault("files", {})[state_key] = entry


def generate_exploration_audio(
    source_file: Path,
    locale: LocaleConfig,
    config: Config,
    api_key: str,
    force: bool,
    state: dict[str, Any],
) -> bool:
    _, meta, _ = split_front_matter(source_file.read_text(encoding="utf-8"))
    audio_name = resolve_audio_name(source_file, meta, config)
    audio_value = audio_frontmatter_value(locale, audio_name)

    locale.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = locale.output_dir / f"{audio_name}.mp3"
    state_key = f"{locale.name}/{source_file.stem}"
    source_hash = sha256_file(source_file)
    previous = state.get("files", {}).get(state_key, {})

    if not force and previous.get("source_sha256") == source_hash and output_file.exists():
        if update_frontmatter(source_file, audio_value, locale.audio_title):
            print(f"update {state_key} frontmatter")
        else:
            print(f"skip {state_key} (unchanged)")
        return False

    if not force and output_file.exists() and not previous:
        record_state_entry(
            state,
            state_key,
            source_file,
            output_file,
            source_hash,
            language=locale.language,
            bootstrapped=True,
        )
        if update_frontmatter(source_file, audio_value, locale.audio_title):
            print(f"bootstrap {state_key} from existing audio")
        else:
            print(f"bootstrap {state_key} from existing audio (frontmatter already set)")
        return True

    spoken_text = build_spoken_text(locale, source_file, meta)
    chunks = chunk_text(spoken_text, config.max_chunk_chars)
    print(f"generate {state_key} ({len(chunks)} chunk(s), {len(spoken_text):,} chars)")

    with tempfile.TemporaryDirectory(prefix="exploration-audio-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        chunk_files: list[Path] = []
        for index, chunk in enumerate(chunks, start=1):
            chunk_file = tmp_path / f"chunk_{index:03d}.mp3"
            audio_bytes = synthesize_chunk(chunk, config, api_key, locale.language)
            chunk_file.write_bytes(audio_bytes)
            chunk_files.append(chunk_file)
            print(f"  chunk {index}/{len(chunks)} ({len(chunk):,} chars)")
            time.sleep(0.4)

        concat_mp3_files(chunk_files, output_file)

    record_state_entry(
        state,
        state_key,
        source_file,
        output_file,
        source_hash,
        chunks=len(chunks),
        chars=len(spoken_text),
        language=locale.language,
    )
    update_frontmatter(source_file, audio_value, locale.audio_title)
    print(f"  wrote {output_file.relative_to(ROOT)} ({output_file.stat().st_size // 1024} KB)")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--locale", help="Generate one locale only")
    parser.add_argument("--file", help="Generate one exploration markdown filename")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = load_config()
    api_key = os.environ.get(config.api_key_env, "").strip()
    if not api_key and not args.dry_run:
        print(f"Error: {config.api_key_env} is not set.", file=sys.stderr)
        sys.exit(1)

    if args.locale and args.locale not in config.locales:
        print(f"Error: unknown locale {args.locale!r}. Available: {', '.join(config.locales)}", file=sys.stderr)
        sys.exit(1)

    state = load_state(config.state_file)
    locales = [config.locales[args.locale]] if args.locale else list(config.locales.values())

    if args.dry_run:
        for locale in locales:
            for source_file in discover_explorations(locale):
                if args.file and source_file.name != args.file:
                    continue
                audio_name = resolve_audio_name(
                    source_file,
                    split_front_matter(source_file.read_text(encoding="utf-8"))[1],
                    config,
                )
                output_file = locale.output_dir / f"{audio_name}.mp3"
                status = "ready" if output_file.exists() else "missing"
                print(f"{locale.name}/{source_file.stem}: audio={status}")
        return

    changed = 0
    for locale in locales:
        for source_file in discover_explorations(locale):
            if args.file and source_file.name != args.file:
                continue
            if generate_exploration_audio(source_file, locale, config, api_key, args.force, state):
                changed += 1
                save_state(config.state_file, state)

    save_state(config.state_file, state)
    print(f"Done. Updated {changed} exploration audio file(s).")


if __name__ == "__main__":
    main()