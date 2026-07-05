#!/usr/bin/env python3
"""Restore protected placeholders in translated exploration articles."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "content" / "explorations"

TOKEN_RE = re.compile(r"<<\s*PROTECTED_(\d+)\s*>>", re.IGNORECASE)

FA_LEAK_FIXES: list[tuple[str, str]] = [
    (r"\binferior\b", "ضعیف‌تر"),
    (r"\bliabilities\b", "بارها"),
]


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


def english_token_map(text: str) -> dict[str, str]:
    protector = Protector()
    protector.protect(text)
    return protector.tokens


def restore_tokens(text: str, token_map: dict[str, str]) -> tuple[str, int]:
    restored = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal restored
        key = f"<<PROTECTED_{match.group(1)}>>"
        if key in token_map:
            restored += 1
            return token_map[key]
        return match.group(0)

    return TOKEN_RE.sub(repl, text), restored


def fix_english_leaks(text: str, fixes: list[tuple[str, str]]) -> tuple[str, int]:
    count = 0
    for pattern, replacement in fixes:
        text, n = re.subn(pattern, replacement, text, flags=re.IGNORECASE)
        count += n
    return text, count


def target_files(locale: str) -> list[Path]:
    target_dir = ROOT / "content" / locale / "explorations"
    files: list[Path] = []
    for path in sorted(target_dir.glob("*.md")):
        if path.name == "_index.md":
            continue
        rel = path.name
        if (SOURCE_DIR / rel).exists():
            files.append(path)
    return files


def fix_locale(locale: str, dry_run: bool) -> dict[str, int]:
    leak_fixes = FA_LEAK_FIXES if locale == "fa" else []
    total = {"files": 0, "tokens": 0, "leaks": 0}

    for target in target_files(locale):
        source = SOURCE_DIR / target.name
        en_text = source.read_text(encoding="utf-8")
        locale_text = target.read_text(encoding="utf-8")
        token_map = english_token_map(en_text)

        updated = locale_text
        updated, tokens = restore_tokens(updated, token_map)
        updated, leaks = fix_english_leaks(updated, leak_fixes)

        if updated != locale_text:
            total["files"] += 1
            total["tokens"] += tokens
            total["leaks"] += leaks
            if not dry_run:
                target.write_text(updated, encoding="utf-8")
            print(
                f"{'would fix' if dry_run else 'fixed'} {target.relative_to(ROOT)}: "
                f"tokens={tokens} leaks={leaks}"
            )

    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale", choices=["fa", "vi", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    locales = ["fa", "vi"] if args.locale == "all" else [args.locale]
    grand = {"files": 0, "tokens": 0, "leaks": 0}

    for locale in locales:
        stats = fix_locale(locale, args.dry_run)
        for key in grand:
            grand[key] += stats[key]

    print(
        f"Done. {'Would update' if args.dry_run else 'Updated'} {grand['files']} file(s): "
        f"{grand['tokens']} tokens, {grand['leaks']} leak fixes."
    )


if __name__ == "__main__":
    main()