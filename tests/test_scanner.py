"""Behavioural tests for the scanner, driven entirely by fixture folders."""

from pathlib import Path

from mdlinkcheck.scanner import scan

FIXTURES = Path(__file__).parent / "fixtures"


def problem_lines(fixture: str) -> list[str]:
    return [issue.format() for issue in scan(FIXTURES / fixture).problems]


def test_missing_relative_file_is_reported():
    assert (
        "README.md:4: broken link: docs/missing.md (file not found)"
        in problem_lines("broken")
    )


def test_missing_same_file_anchor_is_reported():
    assert (
        "README.md:5: broken link: #no-such-heading (heading not found)"
        in problem_lines("broken")
    )


def test_missing_cross_file_anchor_is_reported():
    assert (
        "README.md:8: broken link: docs/guide.md#missing-section (heading not found)"
        in problem_lines("broken")
    )


def test_existing_file_and_anchor_are_not_problems():
    lines = problem_lines("broken")
    assert not any("docs/guide.md " in line for line in lines)
    assert not any("guide.md#getting-started" in line for line in lines)
    assert not any("#broken-sample" in line for line in lines)


def test_fenced_and_inline_code_are_ignored():
    lines = problem_lines("broken")
    assert not any("docs/not-real.md" in line for line in lines)


def test_fence_variants_are_ignored():
    lines = problem_lines("fences")
    assert lines == [
        "README.md:19: broken link: docs/missing-d.md (file not found)"
    ]


def test_images_are_ignored():
    assert not any("assets/missing.png" in line for line in problem_lines("broken"))


def test_external_links_are_unchecked_not_broken():
    result = scan(FIXTURES / "broken")
    assert result.problems and not any(
        "example.com" in issue.format() for issue in result.problems
    )
    assert [issue.format() for issue in result.unchecked] == [
        "README.md:9: unchecked: https://example.com/page"
    ]


def test_anchor_slugs_cover_duplicates_setext_unicode_and_encoding():
    result = scan(FIXTURES / "slugs")
    assert [issue.format() for issue in result.problems] == []
    assert result.files_scanned == 4


def test_clean_fixture_has_no_problems():
    result = scan(FIXTURES / "clean")
    assert result.problems == []
    assert [issue.format() for issue in result.unchecked] == [
        "README.md:5: unchecked: https://example.com"
    ]
    assert result.files_scanned == 2


def test_heading_edge_cases_and_linked_images():
    result = scan(FIXTURES / "edge")
    assert [issue.format() for issue in result.problems] == [
        "README.md:13: broken link: #release-notes-2 (heading not found)",
        "README.md:17: broken link: docs/nope.md (file not found)",
    ]
    assert [issue.format() for issue in result.unchecked] == [
        "README.md:11: unchecked: //cdn.example.com/lib.js"
    ]


def test_closing_hashes_and_links_in_headings_are_handled():
    result = scan(FIXTURES / "edge")
    lines = [issue.format() for issue in result.problems]
    assert not any("#release-notes " in line for line in lines)
    assert "README.md:17: broken link: docs/nope.md (file not found)" in lines


def test_blockquote_fences_and_badges_are_ignored():
    lines = problem_lines("edge")
    assert not any("docs/not-there.md" in line for line in lines)
    assert not any("assets/missing.png" in line for line in lines)
    assert not any("docs/ci.md " in line for line in lines)


def test_output_is_sorted_and_paths_are_relative():
    result = scan(FIXTURES / "broken")
    formatted = [issue.format() for issue in result.problems]
    assert formatted == [
        "README.md:4: broken link: docs/missing.md (file not found)",
        "README.md:5: broken link: #no-such-heading (heading not found)",
        "README.md:8: broken link: docs/guide.md#missing-section (heading not found)",
    ]
