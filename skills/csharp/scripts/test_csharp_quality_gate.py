"""Unit tests for the pure functions in ``csharp_quality_gate``.

Standard library ``unittest`` only, per the gate's no-non-native-dependency
contract. The tests import the module directly and never spawn a subprocess;
the orchestration half (git and dotnet calls) is exercised by the documented
smoke run, not here. The core-parsing cases (diff hunks, lcov merging, path
normalization) are kept in step with the sibling test files
``skills/rust/scripts/test_rust_quality_gate.py`` and
``skills/python/scripts/test_python_quality_gate.py`` so a drifted copy of the
shared core fails its own suite. Run with::

    python -m unittest discover -s skills/csharp/scripts
"""

from __future__ import annotations

import contextlib
import io
import textwrap
import unittest

from csharp_quality_gate import (
    CoverageReport,
    coverage_passes,
    intersect,
    is_bodyless_cs,
    is_excluded,
    looks_like_lcov,
    map_changed_projects,
    mutation_scope_empty,
    normalize_sf_path,
    parse_added_lines,
    parse_args,
    parse_lcov,
    strip_control,
)


class ParseAddedLinesTest(unittest.TestCase):
    """Hunk parsing over ``git diff`` output."""

    def test_simple_addition(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/App/Order.cs b/src/App/Order.cs
            index 1111111..2222222 100644
            --- a/src/App/Order.cs
            +++ b/src/App/Order.cs
            @@ -4,0 +5,2 @@
            +public int AddedOne() => 1;
            +public int AddedTwo() => 2;
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/App/Order.cs": {5, 6}})

    def test_multiple_hunks_one_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/App/Order.cs b/src/App/Order.cs
            --- a/src/App/Order.cs
            +++ b/src/App/Order.cs
            @@ -1,0 +2 @@
            +public int First() => 1;
            @@ -10,0 +12,2 @@
            +public int Second() => 2;
            +public int Third() => 3;
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/App/Order.cs": {2, 12, 13}})

    def test_hunk_header_without_counts_defaults_to_one(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/App/Order.cs b/src/App/Order.cs
            --- a/src/App/Order.cs
            +++ b/src/App/Order.cs
            @@ -3 +3 @@
            -public int Old() => 0;
            +public int New() => 1;
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/App/Order.cs": {3}})

    def test_rename_with_edits(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/OldName.cs b/src/NewName.cs
            similarity index 90%
            rename from src/OldName.cs
            rename to src/NewName.cs
            index 1111111..2222222 100644
            --- a/src/OldName.cs
            +++ b/src/NewName.cs
            @@ -10,0 +11,2 @@
            +public int AddedOne() => 1;
            +public int AddedTwo() => 2;
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/NewName.cs": {11, 12}})

    def test_pure_rename_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/OldName.cs b/src/NewName.cs
            similarity index 100%
            rename from src/OldName.cs
            rename to src/NewName.cs
            """
        )
        self.assertEqual(parse_added_lines(diff), {})

    def test_deletion_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/Gone.cs b/src/Gone.cs
            deleted file mode 100644
            index 1111111..0000000
            --- a/src/Gone.cs
            +++ /dev/null
            @@ -1,3 +0,0 @@
            -public class Gone
            -{
            -}
            """
        )
        self.assertEqual(parse_added_lines(diff), {})

    def test_no_newline_marker_mid_hunk(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/App/Order.cs b/src/App/Order.cs
            --- a/src/App/Order.cs
            +++ b/src/App/Order.cs
            @@ -3 +3 @@
            -old line
            \\ No newline at end of file
            +new line
            \\ No newline at end of file
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/App/Order.cs": {3}})

    def test_c_quoted_path_with_tab_and_octal(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git "a/a\\tb.cs" "b/a\\tb.cs"
            --- "a/a\\tb.cs"
            +++ "b/a\\tb.cs"
            @@ -0,0 +1 @@
            +public class X { }
            diff --git "a/caf\\303\\251.cs" "b/caf\\303\\251.cs"
            --- "a/caf\\303\\251.cs"
            +++ "b/caf\\303\\251.cs"
            @@ -0,0 +1 @@
            +public class Y { }
            """
        )
        self.assertEqual(
            parse_added_lines(diff),
            {"a\tb.cs": {1}, "café.cs": {1}},
        )

    def test_added_line_resembling_headers_stays_body(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/notes.md b/notes.md
            --- a/notes.md
            +++ b/notes.md
            @@ -0,0 +1,3 @@
            ++++ b/Fake.cs
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
            SF:src/App/Order.cs
            DA:1,3
            DA:2,0
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/App/Order.cs": {1: 3, 2: 0}})

    def test_duplicate_sf_blocks_merge_by_summing(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/App/Order.cs
            DA:2,0
            end_of_record
            SF:src/App/Order.cs
            DA:2,3
            DA:9,1
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/App/Order.cs": {2: 3, 9: 1}})

    def test_checksum_third_field_tolerated(self) -> None:
        lcov = "SF:src/App/Order.cs\nDA:7,1,c2VlZA==\nend_of_record\n"
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/App/Order.cs": {7: 1}})

    def test_malformed_da_records_skipped(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/App/Order.cs
            DA:5
            DA:x,y
            DA:6,2
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/App/Order.cs": {6: 2}})

    def test_da_before_any_sf_ignored(self) -> None:
        lcov = "DA:1,1\nSF:src/App/Order.cs\nDA:2,1\nend_of_record\n"
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/App/Order.cs": {2: 1}})

    def test_absolute_sf_paths_normalized(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:/repo/src/App/Order.cs
            DA:1,1
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/App/Order.cs": {1: 1}})


class NormalizeSfPathTest(unittest.TestCase):
    """``SF:`` path normalization to repo-relative POSIX form."""

    def test_windows_backslash_and_case_insensitive_root(self) -> None:
        self.assertEqual(
            normalize_sf_path("C:\\Repo\\src\\Order.cs", "c:/repo"), "src/Order.cs"
        )

    def test_posix_absolute_under_root(self) -> None:
        self.assertEqual(
            normalize_sf_path("/home/user/repo/src/Order.cs", "/home/user/repo"),
            "src/Order.cs",
        )

    def test_relative_path_kept_as_is(self) -> None:
        self.assertEqual(normalize_sf_path("src/Order.cs", "/repo"), "src/Order.cs")

    def test_absolute_outside_root_kept(self) -> None:
        self.assertEqual(
            normalize_sf_path("/elsewhere/X.cs", "/home/user/repo"), "/elsewhere/X.cs"
        )

    def test_path_equal_to_root(self) -> None:
        self.assertEqual(normalize_sf_path("/repo", "/repo/"), "")


class LooksLikeLcovTest(unittest.TestCase):
    """Grammar sniff separating lcov files from other test attachments."""

    def test_real_lcov_accepted(self) -> None:
        text = "TN:\nSF:src/App/Order.cs\nDA:1,1\nend_of_record\n"
        self.assertTrue(looks_like_lcov(text))

    def test_sf_without_end_of_record_rejected(self) -> None:
        self.assertFalse(looks_like_lcov("SF:src/App/Order.cs\nDA:1,1\n"))

    def test_end_of_record_without_sf_rejected(self) -> None:
        self.assertFalse(looks_like_lcov("DA:1,1\nend_of_record\n"))

    def test_mid_line_sf_mention_rejected(self) -> None:
        text = "log: found SF:src/App/Order.cs in output\nend_of_record\n"
        self.assertFalse(looks_like_lcov(text))

    def test_empty_text_rejected(self) -> None:
        self.assertFalse(looks_like_lcov(""))


class IsExcludedTest(unittest.TestCase):
    """Default and user-supplied coverage exclusions."""

    def test_test_segments_case_insensitive(self) -> None:
        for path in (
            "tests/App.Tests/OrderServiceTests.cs",
            "src/Test/Helper.cs",
            "SRC/TESTS/Helper.cs",
            "tests/MyApp.Tests/Fixture.cs",
            "src/MyApp.tests/Fixture.cs",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_excluded(path, []))

    def test_tests_suffix_and_designer_basenames(self) -> None:
        for path in (
            "src/App/OrderServiceTests.cs",
            "src/App/orderservicetests.cs",
            "src/App/Form1.Designer.cs",
            "src/App/form1.designer.cs",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_excluded(path, []))

    def test_production_file_not_excluded(self) -> None:
        self.assertFalse(is_excluded("src/App/OrderService.cs", []))
        self.assertFalse(is_excluded("src/App/ContestService.cs", []))
        self.assertFalse(is_excluded("src/Testing/Attestation.cs", []))

    def test_user_glob_against_path_and_basename(self) -> None:
        self.assertTrue(is_excluded("src/Generated/Schema.cs", ["src/Generated/*"]))
        self.assertTrue(is_excluded("src/Deep/Nested/Schema.cs", ["Schema.cs"]))
        self.assertFalse(is_excluded("src/App/Order.cs", ["src/Generated/*"]))


class IsBodylessCsTest(unittest.TestCase):
    """Content classifier for files that compile to no method bodies."""

    def test_pure_interface_file(self) -> None:
        content = textwrap.dedent(
            """\
            namespace App.Services;

            public interface IOrderRepository
            {
                Task SaveAsync(Order order, CancellationToken cancellationToken);
            }
            """
        )
        self.assertTrue(is_bodyless_cs(content))

    def test_pure_enum_file(self) -> None:
        content = textwrap.dedent(
            """\
            namespace App.Models;

            public enum OrderStatus
            {
                Pending = 1,
                Shipped = 2,
            }
            """
        )
        self.assertTrue(is_bodyless_cs(content))

    def test_delegate_only_file(self) -> None:
        content = "namespace App;\n\npublic delegate void OrderHandler(Order order);\n"
        self.assertTrue(is_bodyless_cs(content))

    def test_mixed_file_with_class_is_coverable(self) -> None:
        content = textwrap.dedent(
            """\
            namespace App;

            public interface IOrderService
            {
                void Ship(Order order);
            }

            internal class OrderService : IOrderService
            {
                public void Ship(Order order) { }
            }
            """
        )
        self.assertFalse(is_bodyless_cs(content))

    def test_top_level_statements_are_coverable(self) -> None:
        content = 'using System;\n\nConsole.WriteLine("hello");\n'
        self.assertFalse(is_bodyless_cs(content))

    def test_class_keyword_in_comment_or_string_ignored(self) -> None:
        content = textwrap.dedent(
            """\
            namespace App;

            // Implemented by the OrderService class in App.Services.
            public interface IOrderService
            {
                /* class-level contract */
                string Describe(); // returns "class summary"
            }
            """
        )
        self.assertTrue(is_bodyless_cs(content))

    def test_class_constraint_is_not_a_declaration(self) -> None:
        content = textwrap.dedent(
            """\
            namespace App;

            public interface IRepository<T> where T : class
            {
                T Load(int id);
            }
            """
        )
        self.assertTrue(is_bodyless_cs(content))


class MapChangedProjectsTest(unittest.TestCase):
    """Nearest-``.csproj``-ancestor mapping for the multi-project warning."""

    def test_single_project(self) -> None:
        projects, unmapped = map_changed_projects(
            ["src/App/Services/OrderService.cs", "src/App/Models/Order.cs"],
            ["src/App/App.csproj", "tests/App.Tests/App.Tests.csproj"],
        )
        self.assertEqual(projects, {"src/App"})
        self.assertEqual(unmapped, [])

    def test_two_projects_detected(self) -> None:
        projects, unmapped = map_changed_projects(
            ["src/App/OrderService.cs", "src/Billing/Invoice.cs"],
            ["src/App/App.csproj", "src/Billing/Billing.csproj"],
        )
        self.assertEqual(projects, {"src/App", "src/Billing"})
        self.assertEqual(unmapped, [])

    def test_file_without_csproj_ancestor(self) -> None:
        projects, unmapped = map_changed_projects(
            ["scripts/Loose.cs"],
            ["src/App/App.csproj"],
        )
        self.assertEqual(projects, set())
        self.assertEqual(unmapped, ["scripts/Loose.cs"])

    def test_root_level_project(self) -> None:
        projects, unmapped = map_changed_projects(
            ["Program.cs"],
            ["App.csproj"],
        )
        self.assertEqual(projects, {""})
        self.assertEqual(unmapped, [])


class MutationScopeEmptyTest(unittest.TestCase):
    """Scope-emptiness predicate that drives the mutation short-circuit."""

    def test_empty_added_set(self) -> None:
        self.assertEqual(mutation_scope_empty({}, []), (True, False))

    def test_test_only_additions(self) -> None:
        added = {"tests/App.Tests/OrderServiceTests.cs": {1, 2}}
        self.assertEqual(mutation_scope_empty(added, []), (True, False))

    def test_non_csharp_additions(self) -> None:
        added = {"README.md": {1}, "src/app.py": {2}}
        self.assertEqual(mutation_scope_empty(added, []), (True, False))

    def test_user_globs_emptied_the_scope(self) -> None:
        added = {"src/Generated/Schema.cs": {1}}
        self.assertEqual(mutation_scope_empty(added, ["src/Generated/*"]), (True, True))

    def test_mixed_scope_is_not_empty(self) -> None:
        added = {"src/App/Order.cs": {1}, "tests/App.Tests/T.cs": {2}}
        self.assertEqual(mutation_scope_empty(added, []), (False, False))


class IntersectTest(unittest.TestCase):
    """Added-lines-versus-lcov intersection with the counted-uncovered rule."""

    def test_covered_uncovered_and_noncoverable_lines(self) -> None:
        report = intersect(
            {"src/App/Order.cs": {1, 2, 3}},
            {"src/App/Order.cs": {1: 1, 2: 0}},
            [],
            set(),
        )
        self.assertEqual(report.per_file, [("src/App/Order.cs", 1, 2)])
        self.assertEqual(report.uncovered, [("src/App/Order.cs", 2)])
        self.assertEqual(report.not_instrumented, [])
        self.assertEqual((report.total_covered, report.total_coverable), (1, 2))

    def test_non_csharp_and_excluded_files_skipped(self) -> None:
        report = intersect(
            {"README.md": {5}, "tests/App.Tests/T.cs": {1}},
            {},
            [],
            set(),
        )
        self.assertEqual(report, CoverageReport())

    def test_all_uninstrumented_diff_counts_fully_uncovered(self) -> None:
        report = intersect({"src/App/New.cs": {1, 2, 3}}, {}, [], set())
        self.assertEqual(report.not_instrumented, [("src/App/New.cs", 3)])
        self.assertEqual(report.per_file, [])
        self.assertEqual((report.total_covered, report.total_coverable), (0, 3))

    def test_uninstrumented_file_drags_instrumented_sibling_ratio(self) -> None:
        report = intersect(
            {"src/App/Old.cs": {1, 2}, "src/App/New.cs": {1, 2}},
            {"src/App/Old.cs": {1: 1, 2: 1}},
            [],
            set(),
        )
        self.assertEqual(report.per_file, [("src/App/Old.cs", 2, 2)])
        self.assertEqual(report.not_instrumented, [("src/App/New.cs", 2)])
        self.assertEqual((report.total_covered, report.total_coverable), (2, 4))

    def test_bodyless_file_excluded_from_ratio(self) -> None:
        report = intersect(
            {"src/App/IOrderService.cs": {1, 2}},
            {},
            [],
            {"src/App/IOrderService.cs"},
        )
        self.assertEqual(report.non_coverable, ["src/App/IOrderService.cs"])
        self.assertEqual(report.not_instrumented, [])
        self.assertEqual((report.total_covered, report.total_coverable), (0, 0))

    def test_instrumented_file_with_no_coverable_added_lines(self) -> None:
        report = intersect(
            {"src/App/Doc.cs": {5}}, {"src/App/Doc.cs": {1: 1}}, [], set()
        )
        self.assertEqual(report, CoverageReport())


class ParseArgsTest(unittest.TestCase):
    """CLI parsing, with usage errors remapped to exit 64."""

    def test_defaults(self) -> None:
        args = parse_args([])
        self.assertEqual(args.cov_threshold, 90)
        self.assertEqual(args.test_target, ".")
        self.assertIsNone(args.stryker_dir)
        self.assertIsNone(args.stryker_solution)

    def test_threshold_bounds_accepted(self) -> None:
        self.assertEqual(parse_args(["--cov-threshold", "0"]).cov_threshold, 0)
        self.assertEqual(parse_args(["--cov-threshold", "100"]).cov_threshold, 100)

    def test_threshold_out_of_range_or_malformed_exits_64(self) -> None:
        for bad in ("101", "-1", "abc"):
            with self.subTest(value=bad):
                with (
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as ctx,
                ):
                    parse_args(["--cov-threshold", bad])
                self.assertEqual(ctx.exception.code, 64)

    def test_leading_dash_path_values_exit_64(self) -> None:
        for flag in (
            "--lcov-file",
            "--test-target",
            "--stryker-dir",
            "--stryker-solution",
        ):
            with self.subTest(flag=flag):
                with (
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as ctx,
                ):
                    parse_args([flag, "--evil"])
                self.assertEqual(ctx.exception.code, 64)

    def test_solution_and_dir_together_exit_64(self) -> None:
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as ctx,
        ):
            parse_args(["--stryker-solution", "App.sln", "--stryker-dir", "tests"])
        self.assertEqual(ctx.exception.code, 64)


class CoveragePassesTest(unittest.TestCase):
    """Integer threshold check."""

    def test_exactly_at_threshold_passes(self) -> None:
        self.assertIs(coverage_passes(9, 10, 90), True)

    def test_below_threshold_fails(self) -> None:
        self.assertIs(coverage_passes(89, 100, 90), False)

    def test_full_coverage_passes(self) -> None:
        self.assertIs(coverage_passes(2, 2, 90), True)

    def test_nothing_to_check_is_neither(self) -> None:
        self.assertIsNone(coverage_passes(0, 0, 90))


class StripControlTest(unittest.TestCase):
    """Sanitization of source lines echoed into the report."""

    def test_ansi_sequences_removed(self) -> None:
        self.assertEqual(strip_control("\x1b[31mred\x1b[0m text"), "red text")

    def test_control_characters_removed_tab_kept(self) -> None:
        self.assertEqual(strip_control("a\x07b\tc\x00d"), "ab\tcd")


if __name__ == "__main__":
    unittest.main()
