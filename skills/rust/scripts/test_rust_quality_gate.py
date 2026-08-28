"""Unit tests for the pure functions in ``rust_quality_gate``.

Standard library ``unittest`` only, per the gate's no-non-native-dependency
contract. The tests import the module directly and never spawn a subprocess;
the orchestration half (git and cargo calls) is exercised by the documented
smoke run, not here. Run with::

    python -m unittest discover -s skills/rust/scripts
"""

from __future__ import annotations

import contextlib
import io
import textwrap
import unittest

from rust_quality_gate import (
    CoverageReport,
    _size_counted_lines,
    coverage_passes,
    drop_test_module_lines,
    intersect,
    is_excluded,
    is_size_skipped,
    is_size_test_file,
    normalize_sf_path,
    parse_added_lines,
    parse_args,
    parse_diff_file_status,
    parse_lcov,
    size_trailing_test_start,
    size_verdict,
    strip_cfg_test_regions,
)


class ParseAddedLinesTest(unittest.TestCase):
    """Hunk parsing over ``git diff`` output."""

    def test_simple_addition(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/lib.rs b/src/lib.rs
            index 1111111..2222222 100644
            --- a/src/lib.rs
            +++ b/src/lib.rs
            @@ -4,0 +5,2 @@
            +fn added_one() {}
            +fn added_two() {}
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/lib.rs": {5, 6}})

    def test_multiple_hunks_one_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/lib.rs b/src/lib.rs
            --- a/src/lib.rs
            +++ b/src/lib.rs
            @@ -1,0 +2 @@
            +fn first() {}
            @@ -10,0 +12,2 @@
            +fn second() {}
            +fn third() {}
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/lib.rs": {2, 12, 13}})

    def test_hunk_header_without_counts_defaults_to_one(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/lib.rs b/src/lib.rs
            --- a/src/lib.rs
            +++ b/src/lib.rs
            @@ -3 +3 @@
            -fn old() {}
            +fn new() {}
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/lib.rs": {3}})

    def test_rename_with_edits(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old_name.rs b/src/new_name.rs
            similarity index 90%
            rename from src/old_name.rs
            rename to src/new_name.rs
            index 1111111..2222222 100644
            --- a/src/old_name.rs
            +++ b/src/new_name.rs
            @@ -10,0 +11,2 @@
            +fn added_one() {}
            +fn added_two() {}
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/new_name.rs": {11, 12}})

    def test_pure_rename_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old_name.rs b/src/new_name.rs
            similarity index 100%
            rename from src/old_name.rs
            rename to src/new_name.rs
            """
        )
        self.assertEqual(parse_added_lines(diff), {})

    def test_deletion_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/gone.rs b/src/gone.rs
            deleted file mode 100644
            index 1111111..0000000
            --- a/src/gone.rs
            +++ /dev/null
            @@ -1,3 +0,0 @@
            -fn a() {}
            -fn b() {}
            -fn c() {}
            """
        )
        self.assertEqual(parse_added_lines(diff), {})

    def test_no_newline_marker_mid_hunk(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/lib.rs b/src/lib.rs
            --- a/src/lib.rs
            +++ b/src/lib.rs
            @@ -3 +3 @@
            -old line
            \\ No newline at end of file
            +new line
            \\ No newline at end of file
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/lib.rs": {3}})

    def test_c_quoted_path_with_tab_and_octal(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git "a/a\\tb.rs" "b/a\\tb.rs"
            --- "a/a\\tb.rs"
            +++ "b/a\\tb.rs"
            @@ -0,0 +1 @@
            +fn x() {}
            diff --git "a/caf\\303\\251.rs" "b/caf\\303\\251.rs"
            --- "a/caf\\303\\251.rs"
            +++ "b/caf\\303\\251.rs"
            @@ -0,0 +1 @@
            +fn y() {}
            """
        )
        self.assertEqual(
            parse_added_lines(diff),
            {"a\tb.rs": {1}, "caf\u00e9.rs": {1}},
        )

    def test_added_line_resembling_headers_stays_body(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/notes.md b/notes.md
            --- a/notes.md
            +++ b/notes.md
            @@ -0,0 +1,3 @@
            ++++ b/fake.rs
            +@@ -1 +1 @@
            +diff --git a/x b/x
            """
        )
        self.assertEqual(parse_added_lines(diff), {"notes.md": {1, 2, 3}})

    def test_empty_diff(self) -> None:
        self.assertEqual(parse_added_lines(""), {})


class ParseLcovTest(unittest.TestCase):
    """``SF:``/``DA:`` record parsing."""

    def test_basic_records(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/lib.rs
            DA:1,3
            DA:2,0
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/lib.rs": {1: 3, 2: 0}})

    def test_duplicate_sf_blocks_merge_by_summing(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/lib.rs
            DA:2,0
            end_of_record
            SF:src/lib.rs
            DA:2,3
            DA:9,1
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/lib.rs": {2: 3, 9: 1}})

    def test_checksum_third_field_tolerated(self) -> None:
        lcov = "SF:src/lib.rs\nDA:7,1,c2VlZA==\nend_of_record\n"
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/lib.rs": {7: 1}})

    def test_malformed_da_records_skipped(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/lib.rs
            DA:5
            DA:x,y
            DA:6,2
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/lib.rs": {6: 2}})

    def test_da_before_any_sf_ignored(self) -> None:
        lcov = "DA:1,1\nSF:src/lib.rs\nDA:2,1\nend_of_record\n"
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/lib.rs": {2: 1}})

    def test_absolute_sf_paths_normalized(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:/repo/src/lib.rs
            DA:1,1
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/lib.rs": {1: 1}})


class NormalizeSfPathTest(unittest.TestCase):
    """``SF:`` path normalization to repo-relative POSIX form."""

    def test_windows_backslash_and_case_insensitive_root(self) -> None:
        self.assertEqual(
            normalize_sf_path("C:\\Repo\\src\\lib.rs", "c:/repo"), "src/lib.rs"
        )

    def test_posix_absolute_under_root(self) -> None:
        self.assertEqual(
            normalize_sf_path("/home/user/repo/src/lib.rs", "/home/user/repo"),
            "src/lib.rs",
        )

    def test_relative_path_kept_as_is(self) -> None:
        self.assertEqual(normalize_sf_path("src/lib.rs", "/repo"), "src/lib.rs")

    def test_absolute_outside_root_kept(self) -> None:
        self.assertEqual(
            normalize_sf_path("/elsewhere/x.rs", "/home/user/repo"), "/elsewhere/x.rs"
        )

    def test_path_equal_to_root(self) -> None:
        self.assertEqual(normalize_sf_path("/repo", "/repo/"), "")


class StripCfgTestRegionsTest(unittest.TestCase):
    """Trailing ``#[cfg(test)]`` module detection, fail-open by design."""

    def test_trailing_test_module_returns_attribute_line(self) -> None:
        content = textwrap.dedent(
            """\
            fn prod() {
                1
            }

            #[cfg(test)]
            mod tests {
                #[test]
                fn t() {
                    assert!(true);
                }
            }
            """
        )
        self.assertEqual(strip_cfg_test_regions(content), 5)

    def test_module_followed_by_production_code_fails_open(self) -> None:
        content = textwrap.dedent(
            """\
            #[cfg(test)]
            mod tests {
                fn t() {}
            }

            fn prod() {
                1
            }
            """
        )
        self.assertIsNone(strip_cfg_test_regions(content))

    def test_unbalanced_brace_in_string_fails_open(self) -> None:
        content = 'fn prod() {}\n\n#[cfg(test)]\nmod tests {\n    fn t() { let s = "}"; }\n}\n'
        self.assertIsNone(strip_cfg_test_regions(content))

    def test_balanced_braces_in_string_still_strips(self) -> None:
        content = 'fn prod() {}\n\n#[cfg(test)]\nmod tests {\n    fn t() { let s = "{}"; }\n}\n'
        self.assertEqual(strip_cfg_test_regions(content), 3)

    def test_no_test_module(self) -> None:
        self.assertIsNone(strip_cfg_test_regions("fn prod() {\n    1\n}\n"))

    def test_attribute_without_mod(self) -> None:
        self.assertIsNone(strip_cfg_test_regions("#[cfg(test)]\nfn helper() {}\n"))

    def test_attribute_stack_between_cfg_and_mod(self) -> None:
        content = "#[cfg(test)]\n#[allow(dead_code)]\nmod tests {\n    fn t() {}\n}\n"
        self.assertEqual(strip_cfg_test_regions(content), 1)

    def test_trailing_blank_lines_after_close(self) -> None:
        content = "#[cfg(test)]\nmod tests {\n    fn t() {}\n}\n\n\n"
        self.assertEqual(strip_cfg_test_regions(content), 1)

    def test_empty_file(self) -> None:
        self.assertIsNone(strip_cfg_test_regions(""))

    def test_unclosed_module_fails_open(self) -> None:
        content = "#[cfg(test)]\nmod tests {\n    fn t() {}\n"
        self.assertIsNone(strip_cfg_test_regions(content))


class DropTestModuleLinesTest(unittest.TestCase):
    """Removal of added lines that fall inside the stripped region."""

    def test_lines_at_and_after_strip_point_dropped(self) -> None:
        self.assertEqual(drop_test_module_lines({1, 2, 3, 4, 5}, 3), {1, 2})

    def test_none_strip_point_keeps_everything(self) -> None:
        self.assertEqual(drop_test_module_lines({1, 2, 3}, None), {1, 2, 3})


class IsExcludedTest(unittest.TestCase):
    """Default and user-supplied coverage exclusions."""

    def test_root_level_tests_directory(self) -> None:
        self.assertTrue(is_excluded("tests/integration.rs", []))

    def test_nested_tests_segment(self) -> None:
        self.assertTrue(is_excluded("crates/app/tests/api.rs", []))

    def test_test_suffix_basenames(self) -> None:
        for path in (
            "src/tests.rs",
            "src/parser_tests.rs",
            "src/parser-tests.rs",
            "src/parser_test.rs",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_excluded(path, []))

    def test_production_file_not_excluded(self) -> None:
        self.assertFalse(is_excluded("src/lib.rs", []))
        self.assertFalse(is_excluded("src/attests.rs", []))

    def test_user_glob_against_path_and_basename(self) -> None:
        self.assertTrue(is_excluded("src/generated/schema.rs", ["src/generated/*"]))
        self.assertTrue(is_excluded("src/deep/nested/schema.rs", ["schema.rs"]))
        self.assertFalse(is_excluded("src/lib.rs", ["src/generated/*"]))


class IntersectTest(unittest.TestCase):
    """Added-lines-versus-lcov intersection."""

    def test_covered_uncovered_and_noncoverable_lines(self) -> None:
        report = intersect(
            {"src/lib.rs": {1, 2, 3}},
            {"src/lib.rs": {1: 1, 2: 0}},
            [],
        )
        self.assertEqual(report.per_file, [("src/lib.rs", 1, 2)])
        self.assertEqual(report.uncovered, [("src/lib.rs", 2)])
        self.assertEqual(report.not_instrumented, [])
        self.assertEqual((report.total_covered, report.total_coverable), (1, 2))

    def test_non_rust_and_excluded_files_skipped(self) -> None:
        report = intersect(
            {"README.md": {5}, "tests/it.rs": {1}},
            {},
            [],
        )
        self.assertEqual(report, CoverageReport())

    def test_file_without_sf_record_reported_not_instrumented(self) -> None:
        report = intersect({"src/new.rs": {1}}, {}, [])
        self.assertEqual(report.not_instrumented, ["src/new.rs"])
        self.assertEqual(report.per_file, [])
        self.assertEqual((report.total_covered, report.total_coverable), (0, 0))

    def test_instrumented_file_with_no_coverable_added_lines(self) -> None:
        report = intersect({"src/doc.rs": {5}}, {"src/doc.rs": {1: 1}}, [])
        self.assertEqual(report, CoverageReport())


class ParseArgsTest(unittest.TestCase):
    """CLI parsing, with usage errors remapped to exit 64."""

    def test_threshold_bounds_accepted(self) -> None:
        self.assertEqual(parse_args(["--cov-threshold", "0"]).cov_threshold, 0)
        self.assertEqual(parse_args(["--cov-threshold", "100"]).cov_threshold, 100)

    def test_threshold_out_of_range_or_malformed_exits_64(self) -> None:
        for bad in ("101", "-1", "abc"):
            with self.subTest(value=bad):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        parse_args(["--cov-threshold", bad])
                self.assertEqual(ctx.exception.code, 64)


class ParseDiffFileStatusTest(unittest.TestCase):
    """New / pre-existing / rename classification from diff headers."""

    def test_new_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/new.rs b/src/new.rs
            new file mode 100644
            index 0000000..1111111
            --- /dev/null
            +++ b/src/new.rs
            @@ -0,0 +1,2 @@
            +fn a() {}
            +fn b() {}
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {"src/new.rs": (True, "src/new.rs")})

    def test_modified_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/lib.rs b/src/lib.rs
            index 1111111..2222222 100644
            --- a/src/lib.rs
            +++ b/src/lib.rs
            @@ -3 +3 @@
            -fn old() {}
            +fn new() {}
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {"src/lib.rs": (False, "src/lib.rs")})

    def test_rename_with_edits_keeps_old_path(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old_name.rs b/src/new_name.rs
            similarity index 90%
            rename from src/old_name.rs
            rename to src/new_name.rs
            index 1111111..2222222 100644
            --- a/src/old_name.rs
            +++ b/src/new_name.rs
            @@ -10,0 +11 @@
            +fn added() {}
            """
        )
        self.assertEqual(
            parse_diff_file_status(diff), {"src/new_name.rs": (False, "src/old_name.rs")}
        )

    def test_deletion_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/gone.rs b/src/gone.rs
            deleted file mode 100644
            index 1111111..0000000
            --- a/src/gone.rs
            +++ /dev/null
            @@ -1,2 +0,0 @@
            -fn a() {}
            -fn b() {}
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {})


class IsSizeTestFileTest(unittest.TestCase):
    """Test-file classification for the size gate (warn-only set)."""

    def test_tests_segment_and_basenames(self) -> None:
        for path in (
            "tests/integration.rs",
            "crates/app/tests/api.rs",
            "src/tests.rs",
            "src/parser_tests.rs",
            "src/parser-tests.rs",
            "src/parser_test.rs",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_size_test_file(path))

    def test_production_files_not_test(self) -> None:
        self.assertFalse(is_size_test_file("src/lib.rs"))
        self.assertFalse(is_size_test_file("src/attests.rs"))


class IsSizeSkippedTest(unittest.TestCase):
    """Only user --exclude globs skip a file from the size gate."""

    def test_no_globs_skips_nothing(self) -> None:
        self.assertFalse(is_size_skipped("src/lib.rs", []))
        self.assertFalse(is_size_skipped("tests/it.rs", []))

    def test_user_glob_against_path_and_basename(self) -> None:
        self.assertTrue(is_size_skipped("src/generated/schema.rs", ["src/generated/*"]))
        self.assertTrue(is_size_skipped("src/deep/nested/schema.rs", ["schema.rs"]))


class SizeVerdictTest(unittest.TestCase):
    """The size policy decision, warn 700 / cap 1500 / allowance 50."""

    def verdict(self, counted, is_new, base, is_test=False):
        return size_verdict(counted, is_new, base, is_test, 700, 1500, 50)

    def test_new_below_warn_is_ok(self) -> None:
        self.assertEqual(self.verdict(699, True, None), "OK")

    def test_new_at_warn_is_warn(self) -> None:
        self.assertEqual(self.verdict(700, True, None), "WARN")

    def test_new_at_cap_is_fail(self) -> None:
        self.assertEqual(self.verdict(1500, True, None), "FAIL")

    def test_new_test_file_at_cap_downgrades_to_warn(self) -> None:
        self.assertEqual(self.verdict(1600, True, None, is_test=True), "WARN")

    def test_preexisting_under_cap_crossing_fails(self) -> None:
        self.assertEqual(self.verdict(1500, False, 1400), "FAIL")

    def test_preexisting_grew_past_allowance_into_warn(self) -> None:
        self.assertEqual(self.verdict(800, False, 700), "WARN")

    def test_preexisting_small_growth_is_ok(self) -> None:
        self.assertEqual(self.verdict(740, False, 700), "OK")

    def test_preexisting_already_over_cap_grew_warns(self) -> None:
        self.assertEqual(self.verdict(1700, False, 1600), "WARN")

    def test_preexisting_already_over_cap_never_fails(self) -> None:
        self.assertNotEqual(self.verdict(3000, False, 1600), "FAIL")


class SizeTrailingTestStartTest(unittest.TestCase):
    """Trailing ``#[cfg(test)]`` run detection for the production-line count."""

    def test_single_trailing_module_returns_attribute_line(self) -> None:
        content = textwrap.dedent(
            """\
            fn prod() {
                1
            }

            #[cfg(test)]
            mod tests {
                #[test]
                fn t() {
                    assert!(true);
                }
            }
            """
        )
        self.assertEqual(size_trailing_test_start(content), 5)

    def test_stacked_trailing_modules_return_first(self) -> None:
        content = textwrap.dedent(
            """\
            fn prod() {}

            #[cfg(test)]
            mod tests {
                fn a() {}
            }

            #[cfg(test)]
            mod proptests {
                fn b() {}
            }
            """
        )
        self.assertEqual(size_trailing_test_start(content), 3)

    def test_mid_file_module_not_subtracted(self) -> None:
        content = textwrap.dedent(
            """\
            #[cfg(test)]
            mod tests {
                fn t() {}
            }

            fn prod() {
                1
            }
            """
        )
        self.assertIsNone(size_trailing_test_start(content))

    def test_production_after_module_not_subtracted(self) -> None:
        content = "#[cfg(test)]\nmod tests {\n    fn t() {}\n}\npub const X: u32 = 1;\n"
        self.assertIsNone(size_trailing_test_start(content))

    def test_attribute_on_non_mod_item_is_not_an_anchor(self) -> None:
        content = "fn prod() {}\n#[cfg(test)]\nfn helper() {}\n"
        self.assertIsNone(size_trailing_test_start(content))

    def test_semicolon_module_form(self) -> None:
        content = "fn prod() {}\n\n#[cfg(test)]\nmod tests;\n"
        self.assertEqual(size_trailing_test_start(content), 3)

    def test_doc_comment_between_attribute_and_mod_tolerated(self) -> None:
        content = "#[cfg(test)]\n/// doc\nmod tests {\n    fn t() {}\n}\n"
        self.assertEqual(size_trailing_test_start(content), 1)

    def test_attribute_stack_between_cfg_and_mod(self) -> None:
        content = "#[cfg(test)]\n#[allow(dead_code)]\nmod tests {\n    fn t() {}\n}\n"
        self.assertEqual(size_trailing_test_start(content), 1)

    def test_pub_and_pub_crate_visibility(self) -> None:
        for header in ("pub mod tests {", "pub(crate) mod tests {"):
            with self.subTest(header=header):
                content = f"#[cfg(test)]\n{header}\n    fn t() {{}}\n}}\n"
                self.assertEqual(size_trailing_test_start(content), 1)

    def test_cfg_all_test_not_recognized(self) -> None:
        content = 'fn prod() {}\n#[cfg(all(test, feature = "x"))]\nmod tests {\n}\n'
        self.assertIsNone(size_trailing_test_start(content))

    def test_unbalanced_brace_in_string_fails_open(self) -> None:
        content = 'fn prod() {}\n\n#[cfg(test)]\nmod tests {\n    fn t() { let s = "}"; }\n}\n'
        self.assertIsNone(size_trailing_test_start(content))

    def test_balanced_braces_in_string_still_strips(self) -> None:
        content = 'fn prod() {}\n\n#[cfg(test)]\nmod tests {\n    fn t() { let s = "{}"; }\n}\n'
        self.assertEqual(size_trailing_test_start(content), 3)

    def test_trailing_blanks_after_close(self) -> None:
        content = "#[cfg(test)]\nmod tests {\n    fn t() {}\n}\n\n\n"
        self.assertEqual(size_trailing_test_start(content), 1)

    def test_trailing_comment_after_close(self) -> None:
        content = "#[cfg(test)]\nmod tests {\n    fn t() {}\n}\n// eof\n"
        self.assertEqual(size_trailing_test_start(content), 1)

    def test_crlf_line_endings(self) -> None:
        content = "fn prod() {}\r\n\r\n#[cfg(test)]\r\nmod tests {\r\n}\r\n"
        self.assertEqual(size_trailing_test_start(content), 3)

    def test_bom_prefix_does_not_break_detection(self) -> None:
        content = "﻿// header\nfn prod() {}\n\n#[cfg(test)]\nmod tests {\n}\n"
        self.assertEqual(size_trailing_test_start(content), 4)

    def test_all_tests_file(self) -> None:
        content = "#[cfg(test)]\nmod tests {\n    fn t() {}\n}\n"
        self.assertEqual(size_trailing_test_start(content), 1)

    def test_no_test_module(self) -> None:
        self.assertIsNone(size_trailing_test_start("fn prod() {\n    1\n}\n"))

    def test_empty_file(self) -> None:
        self.assertIsNone(size_trailing_test_start(""))


class SizeCountedLinesTest(unittest.TestCase):
    """Production line count subtracts the trailing test module."""

    def test_subtracts_trailing_tests(self) -> None:
        content = textwrap.dedent(
            """\
            fn prod() {}

            #[cfg(test)]
            mod tests {
                fn t() {}
            }
            """
        )
        counted, total = _size_counted_lines(content)
        self.assertEqual(total, 6)
        self.assertEqual(counted, 2)

    def test_no_tests_counts_all(self) -> None:
        content = "fn a() {}\nfn b() {}\n"
        self.assertEqual(_size_counted_lines(content), (2, 2))


class CoveragePassesTest(unittest.TestCase):
    """Integer threshold check."""

    def test_exactly_at_threshold_passes(self) -> None:
        self.assertIs(coverage_passes(4, 5, 80), True)

    def test_below_threshold_fails(self) -> None:
        self.assertIs(coverage_passes(79, 100, 80), False)

    def test_full_coverage_passes(self) -> None:
        self.assertIs(coverage_passes(2, 2, 80), True)

    def test_nothing_to_check_is_neither(self) -> None:
        self.assertIsNone(coverage_passes(0, 0, 80))


if __name__ == "__main__":
    unittest.main()
