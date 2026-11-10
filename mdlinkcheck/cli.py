"""Command line interface for mdlinkcheck."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .scanner import ScanResult, scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdlinkcheck",
        description="Report broken relative links and anchors in Markdown files.",
    )
    parser.add_argument("folder", metavar="FOLDER", help="folder scanned recursively for *.md files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.folder)
    if not root.is_dir():
        print(f"mdlinkcheck: not a directory: {args.folder}", file=sys.stderr)
        return 2

    result = scan(root)
    for issue in result.problems:
        print(issue.format())
    for issue in result.unchecked:
        print(issue.format())
    print(_summary(result))
    return 1 if result.problems else 0


def _summary(result: ScanResult) -> str:
    broken = _count(len(result.problems), "broken link")
    unchecked = _count(len(result.unchecked), "unchecked external link")
    files = _count(result.files_scanned, "file")
    return f"{broken}, {unchecked} in {files}"


def _count(amount: int, noun: str) -> str:
    return f"{amount} {noun}" + ("" if amount == 1 else "s")
