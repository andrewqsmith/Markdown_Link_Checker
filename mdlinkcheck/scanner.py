"""Scan Markdown documents for broken relative links and anchors.

Standard library only. Supported subset: ATX and setext headings, fenced code
blocks, CommonMark inline code spans and inline links. Images, reference-style
links, autolinks and other URL schemes are out of scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
EXTERNAL_RE = re.compile(r"^(?:(?:https?:)?//)", re.IGNORECASE)
BLOCKQUOTE_RE = re.compile(r"^(?:[ \t]*>[ \t]?)+")
CLOSING_HASHES_RE = re.compile(r"[ \t]+#+[ \t]*$")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>])")


@dataclass(frozen=True)
class Issue:
    """One reportable line."""

    path: str
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


@dataclass
class ScanResult:
    problems: list[Issue]
    unchecked: list[Issue]
    files_scanned: int


def scan(root: Path) -> ScanResult:
    """Scan every ``*.md`` file under *root* and report link problems."""
    root = Path(root).resolve()
    files = sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".md"),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    headings_cache: dict[Path, set[str]] = {}

    def headings_for(path: Path) -> set[str]:
        resolved = path.resolve()
        if resolved not in headings_cache:
            headings_cache[resolved] = _headings(
                resolved.read_text(encoding="utf-8", errors="replace")
            )
        return headings_cache[resolved]

    problems: list[Issue] = []
    unchecked: list[Issue] = []

    for file in files:
        rel = file.relative_to(root).as_posix()
        text = file.read_text(encoding="utf-8", errors="replace")
        links, headings = _parse_document(text)
        headings_cache[file.resolve()] = headings
        for lineno, destination in links:
            problem, external = _check(destination, file, root, headings_for)
            if problem is not None:
                problems.append(Issue(rel, lineno, problem))
            if external is not None:
                unchecked.append(Issue(rel, lineno, f"unchecked: {external}"))

    problems.sort(key=lambda issue: (issue.path, issue.line, issue.message))
    unchecked.sort(key=lambda issue: (issue.path, issue.line, issue.message))
    return ScanResult(problems=problems, unchecked=unchecked, files_scanned=len(files))


def _check(destination, source: Path, root: Path, headings_for):
    destination = destination.strip()
    if not destination:
        return None, None
    if EXTERNAL_RE.match(destination):
        return None, destination
    if SCHEME_RE.match(destination):
        return None, None  # mailto:, ftp:, ... are out of scope

    path_part, _, anchor = destination.partition("#")
    path_part = path_part.split("?", 1)[0]
    if not path_part:
        target = source
    else:
        decoded = unquote(path_part)
        if decoded.startswith("/"):
            target = root / decoded.lstrip("/")
        else:
            target = source.parent / decoded
        target = target.resolve()

    if not target.exists():
        return f"broken link: {destination} (file not found)", None
    if anchor and target.is_file() and target.suffix.lower() == ".md":
        if unquote(anchor) not in headings_for(target):
            return f"broken link: {destination} (heading not found)", None
    return None, None


def _parse_document(text: str) -> tuple[list[tuple[int, str]], set[str]]:
    """Return ``(line, destination)`` links and the set of heading slugs."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    links: list[tuple[int, str]] = []
    slugs: list[str] = []
    seen: dict[str, int] = {}
    fence: tuple[str, int, bool] | None = None
    paragraph: tuple[int, str] | None = None

    for lineno, raw in enumerate(lines, start=1):
        if fence is not None:
            candidate = BLOCKQUOTE_RE.sub("", raw) if fence[2] else raw
            fence_match = FENCE_RE.match(candidate)
            if (
                fence_match
                and fence_match.group(2)[0] == fence[0]
                and len(fence_match.group(2)) >= fence[1]
                and not fence_match.group(3).strip()
            ):
                fence = None
            paragraph = None
            continue

        candidate = BLOCKQUOTE_RE.sub("", raw)
        fence_match = FENCE_RE.match(candidate)
        if fence_match and not (fence_match.group(2)[0] == "`" and "`" in fence_match.group(3)):
            fence = (
                fence_match.group(2)[0],
                len(fence_match.group(2)),
                candidate != raw,
            )
            paragraph = None
            continue

        heading_match = ATX_RE.match(raw)
        if heading_match:
            heading_text = _heading_text(heading_match.group(2) or "")
            _append_slug(slugs, seen, heading_text)
            links.extend(_find_links(_strip_code_spans(heading_text), lineno))
            paragraph = None
            continue

        setext_match = SETEXT_RE.match(raw)
        if setext_match and paragraph is not None:
            _append_slug(slugs, seen, paragraph[1].strip())
            paragraph = None
            continue

        if not raw.strip():
            paragraph = None
            continue

        links.extend(_find_links(_strip_code_spans(raw), lineno))
        paragraph = (lineno, raw)

    return links, set(slugs)


def _heading_text(heading: str) -> str:
    """Drop an optional ATX closing hash sequence, e.g. ``# Title ##``."""
    return CLOSING_HASHES_RE.sub("", heading).strip()


def _append_slug(slugs: list[str], seen: dict[str, int], heading: str) -> None:
    base = _slug(heading)
    count = seen.get(base, 0)
    seen[base] = count + 1
    slugs.append(base if count == 0 else f"{base}-{count}")


def _headings(text: str) -> set[str]:
    return _parse_document(text)[1]


def _slug(heading: str) -> str:
    text = _strip_inline_formatting(heading)
    chars = []
    for char in text.lower():
        if char.isalnum() or char in "-_":
            chars.append(char)
        elif char.isspace():
            chars.append("-")
    return "".join(chars)


def _strip_inline_formatting(text: str) -> str:
    text = re.sub(r"`+([^`]*)`+", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.replace("*", "").replace("~~", "")


def _strip_code_spans(line: str) -> str:
    """Blank out inline code spans, keeping every other character in place."""
    chars = list(line)
    index = 0
    while index < len(line):
        if line[index] != "`":
            index += 1
            continue
        run_end = index
        while run_end < len(line) and line[run_end] == "`":
            run_end += 1
        run_length = run_end - index
        cursor = run_end
        closing = -1
        while cursor < len(line):
            if line[cursor] == "`":
                candidate_end = cursor
                while candidate_end < len(line) and line[candidate_end] == "`":
                    candidate_end += 1
                if candidate_end - cursor == run_length:
                    closing = candidate_end
                    break
                cursor = candidate_end
            else:
                cursor += 1
        if closing == -1:
            index = run_end
            continue
        for position in range(index, closing):
            chars[position] = " "
        index = closing
    return "".join(chars)


def _find_links(line: str, lineno: int):
    index = 0
    while index < len(line):
        if line[index] != "[":
            index += 1
            continue
        escaped = index > 0 and line[index - 1] == "\\"
        image = index > 0 and line[index - 1] == "!" and not (
            index > 1 and line[index - 2] == "\\"
        )
        closing = _match_bracket(line, index)
        if closing == -1 or closing + 1 >= len(line) or line[closing + 1] != "(":
            index += 1
            continue
        destination, end = _parse_destination(line, closing + 2)
        if destination is None:
            index += 1
            continue
        if not escaped and not image:
            yield lineno, destination
        index = end


def _match_bracket(line: str, start: int) -> int:
    """Index of the ``]`` matching the ``[`` at *start*, honouring nesting."""
    depth = 0
    index = start
    while index < len(line):
        char = line[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _parse_destination(line: str, position: int) -> tuple[str | None, int]:
    length = len(line)
    while position < length and line[position] in " \t":
        position += 1
    if position < length and line[position] == "<":
        end = line.find(">", position + 1)
        if end == -1:
            return None, position
        destination = line[position + 1 : end]
        position = end + 1
    else:
        start = position
        depth = 0
        while position < length:
            char = line[position]
            if char == "\\" and position + 1 < length:
                position += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char in " \t" and depth == 0:
                break
            position += 1
        destination = line[start:position]

    while position < length and line[position] in " \t":
        position += 1
    while position < length and line[position] in "\"'(":
        opener = line[position]
        closer = ")" if opener == "(" else opener
        end = line.find(closer, position + 1)
        if end == -1:
            return None, position
        position = end + 1
        while position < length and line[position] in " \t":
            position += 1
    if position >= length or line[position] != ")":
        return None, position
    return ESCAPE_RE.sub(r"\1", destination), position + 1
