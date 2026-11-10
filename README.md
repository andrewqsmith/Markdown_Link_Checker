# mdlinkcheck

A small command-line tool that scans a folder of Markdown files and reports
broken links. Standard library only — no network access, no dependencies.

## What it checks

| Link | Behaviour |
| --- | --- |
| `[text](docs/guide.md)` | Reported if the relative target file does not exist |
| `[text](#heading)` | Reported if the heading does not exist in the same file |
| `[text](docs/guide.md#heading)` | Reported if the heading does not exist in the target file |
| `[text](https://example.com)` | Never fetched; listed separately as `unchecked` |
| Links in fenced code blocks or inline code | Ignored |
| Images (`![alt](image.png)`) | Ignored |

Anchors are matched with GitHub-style slugs: lowercased, punctuation removed,
spaces turned into hyphens, and duplicate headings suffixed with `-1`, `-2`, …
Percent-encoded paths and fragments are decoded before lookup.

## Install

Requires Python 3.9 or newer.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Or run it straight from a checkout without installing:

```sh
python -m mdlinkcheck <folder>
```

## Usage

```sh
mdlinkcheck <folder>
```

Every `*.md` file under the folder is scanned recursively. Output is one line
per problem as `path:line: message`, then any unchecked external links, then a
one-line summary:

```
$ mdlinkcheck tests/fixtures/broken
README.md:4: broken link: docs/missing.md (file not found)
README.md:5: broken link: #no-such-heading (heading not found)
README.md:8: broken link: docs/guide.md#missing-section (heading not found)
README.md:9: unchecked: https://example.com/page
3 broken links, 1 unchecked external link in 2 files
```

Paths are printed relative to the folder you passed in, and results are sorted
by path and line.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No broken links (unchecked external links do not count) |
| `1` | At least one broken link |
| `2` | Bad arguments: no folder, a missing folder, or a path that is not a directory |

## Supported Markdown subset

- ATX headings (`# Title`) and setext headings (`Title` underlined with `===` or `---`)
- Fenced code blocks (three or more backticks or tildes, including blockquote-nested fences)
- Inline code spans and inline links, with optional `<destination>` and titles

Out of scope: reference-style links, autolinks, `mailto:` and other schemes,
multi-line links or inline code, YAML front matter, and fences indented four or
more spaces inside list items. Hidden and vendor directories (`.git`, `.venv`,
`node_modules`) are not skipped — every `*.md` file is scanned, as specified.

## Development

Tests use pytest and small fixture folders under `tests/fixtures/`; they make no
network calls.

```sh
python -m pytest -q
```

Project layout:

```
mdlinkcheck/
  cli.py        argument parsing, output, exit codes
  scanner.py    Markdown parsing, link and anchor checks
  __main__.py   python -m mdlinkcheck
tests/
  test_cli.py   end-to-end output, ordering, exit codes
  test_scanner.py  per-fixture behaviour
  fixtures/     broken, clean, edge, fences, slugs
```

See [AGENTS.md](AGENTS.md) for the build and test commands used by coding
agents, and [pyproject.toml](pyproject.toml) for packaging metadata.
