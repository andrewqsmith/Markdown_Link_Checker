"""End-to-end CLI tests: exit codes, output format, ordering, summary."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mdlinkcheck", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_broken_folder_exits_one_with_one_line_per_problem():
    result = run(str(FIXTURES / "broken"))
    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "README.md:4: broken link: docs/missing.md (file not found)",
        "README.md:5: broken link: #no-such-heading (heading not found)",
        "README.md:8: broken link: docs/guide.md#missing-section (heading not found)",
        "README.md:9: unchecked: https://example.com/page",
        "3 broken links, 1 unchecked external link in 2 files",
    ]
    assert result.stderr == ""


def test_clean_folder_exits_zero():
    result = run(str(FIXTURES / "clean"))
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "README.md:5: unchecked: https://example.com",
        "0 broken links, 1 unchecked external link in 2 files",
    ]


def test_slugs_folder_exits_zero():
    result = run(str(FIXTURES / "slugs"))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["0 broken links, 0 unchecked external links in 4 files"]


def test_no_arguments_exits_two():
    result = run()
    assert result.returncode == 2
    assert "usage:" in result.stderr.lower()


def test_missing_folder_exits_two():
    result = run(str(FIXTURES / "does-not-exist"))
    assert result.returncode == 2
    assert "not a directory" in result.stderr


def test_file_argument_exits_two():
    result = run(str(FIXTURES / "clean" / "README.md"))
    assert result.returncode == 2
    assert "not a directory" in result.stderr
