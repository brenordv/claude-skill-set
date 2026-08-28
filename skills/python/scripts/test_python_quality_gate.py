"""Unit tests for the pure functions in ``python_quality_gate``.

Standard library ``unittest`` only, per the gate's no-non-native-dependency
contract. The tests import the module directly and never spawn a subprocess;
the orchestration half (git, pytest, and cosmic-ray calls) is exercised by the
documented smoke run, not here. The core-parsing cases (diff hunks, lcov
merging, path normalization) are kept in step with the sibling test files
``skills/rust/scripts/test_rust_quality_gate.py`` and
``skills/csharp/scripts/test_csharp_quality_gate.py`` so a drifted copy of the
shared core fails its own suite. Run with::

    python -m unittest discover -s skills/python/scripts
"""

from __future__ import annotations

import contextlib
import io
import sys
import textwrap
import unittest

from python_quality_gate import (
    EXIT_USAGE,
    CoverageReport,
    GateError,
    build_cosmic_ray_config,
    coverage_passes,
    files_outside_module_path,
    intersect,
    is_excluded,
    is_size_skipped,
    is_size_test_file,
    mutation_scope_empty,
    normalize_sf_path,
    parse_added_lines,
    parse_args,
    parse_diff_file_status,
    parse_lcov,
    parse_survival_rate,
    size_verdict,
    strip_control,
    toml_basic_string,
)

if sys.version_info >= (3, 11):
    import tomllib


class ParseAddedLinesTest(unittest.TestCase):
    """Hunk parsing over ``git diff`` output."""

    def test_simple_addition(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app/orders.py b/src/app/orders.py
            index 1111111..2222222 100644
            --- a/src/app/orders.py
            +++ b/src/app/orders.py
            @@ -4,0 +5,2 @@
            +def added_one(): ...
            +def added_two(): ...
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/app/orders.py": {5, 6}})

    def test_multiple_hunks_one_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app/orders.py b/src/app/orders.py
            --- a/src/app/orders.py
            +++ b/src/app/orders.py
            @@ -1,0 +2 @@
            +def first(): ...
            @@ -10,0 +12,2 @@
            +def second(): ...
            +def third(): ...
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/app/orders.py": {2, 12, 13}})

    def test_hunk_header_without_counts_defaults_to_one(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app/orders.py b/src/app/orders.py
            --- a/src/app/orders.py
            +++ b/src/app/orders.py
            @@ -3 +3 @@
            -def old(): ...
            +def new(): ...
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/app/orders.py": {3}})

    def test_rename_with_edits(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old_name.py b/src/new_name.py
            similarity index 90%
            rename from src/old_name.py
            rename to src/new_name.py
            index 1111111..2222222 100644
            --- a/src/old_name.py
            +++ b/src/new_name.py
            @@ -10,0 +11,2 @@
            +def added_one(): ...
            +def added_two(): ...
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/new_name.py": {11, 12}})

    def test_pure_rename_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old_name.py b/src/new_name.py
            similarity index 100%
            rename from src/old_name.py
            rename to src/new_name.py
            """
        )
        self.assertEqual(parse_added_lines(diff), {})

    def test_deletion_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/gone.py b/src/gone.py
            deleted file mode 100644
            index 1111111..0000000
            --- a/src/gone.py
            +++ /dev/null
            @@ -1,3 +0,0 @@
            -def a(): ...
            -def b(): ...
            -def c(): ...
            """
        )
        self.assertEqual(parse_added_lines(diff), {})

    def test_no_newline_marker_mid_hunk(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app/orders.py b/src/app/orders.py
            --- a/src/app/orders.py
            +++ b/src/app/orders.py
            @@ -3 +3 @@
            -old line
            \\ No newline at end of file
            +new line
            \\ No newline at end of file
            """
        )
        self.assertEqual(parse_added_lines(diff), {"src/app/orders.py": {3}})

    def test_c_quoted_path_with_tab_and_octal(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git "a/a\\tb.py" "b/a\\tb.py"
            --- "a/a\\tb.py"
            +++ "b/a\\tb.py"
            @@ -0,0 +1 @@
            +def x(): ...
            diff --git "a/caf\\303\\251.py" "b/caf\\303\\251.py"
            --- "a/caf\\303\\251.py"
            +++ "b/caf\\303\\251.py"
            @@ -0,0 +1 @@
            +def y(): ...
            """
        )
        self.assertEqual(
            parse_added_lines(diff),
            {"a\tb.py": {1}, "café.py": {1}},
        )

    def test_added_line_resembling_headers_stays_body(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/notes.md b/notes.md
            --- a/notes.md
            +++ b/notes.md
            @@ -0,0 +1,3 @@
            ++++ b/fake.py
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
            SF:src/app/orders.py
            DA:1,3
            DA:2,0
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/app/orders.py": {1: 3, 2: 0}})

    def test_duplicate_sf_blocks_merge_by_summing(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/app/orders.py
            DA:2,0
            end_of_record
            SF:src/app/orders.py
            DA:2,3
            DA:9,1
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/app/orders.py": {2: 3, 9: 1}})

    def test_checksum_third_field_tolerated(self) -> None:
        lcov = "SF:src/app/orders.py\nDA:7,1,c2VlZA==\nend_of_record\n"
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/app/orders.py": {7: 1}})

    def test_malformed_da_records_skipped(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:src/app/orders.py
            DA:5
            DA:x,y
            DA:6,2
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/app/orders.py": {6: 2}})

    def test_da_before_any_sf_ignored(self) -> None:
        lcov = "DA:1,1\nSF:src/app/orders.py\nDA:2,1\nend_of_record\n"
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/app/orders.py": {2: 1}})

    def test_absolute_sf_paths_normalized(self) -> None:
        lcov = textwrap.dedent(
            """\
            SF:/repo/src/app/orders.py
            DA:1,1
            end_of_record
            """
        )
        self.assertEqual(parse_lcov(lcov, "/repo"), {"src/app/orders.py": {1: 1}})


class NormalizeSfPathTest(unittest.TestCase):
    """``SF:`` path normalization to repo-relative POSIX form."""

    def test_windows_backslash_and_case_insensitive_root(self) -> None:
        self.assertEqual(
            normalize_sf_path("C:\\Repo\\src\\orders.py", "c:/repo"), "src/orders.py"
        )

    def test_posix_absolute_under_root(self) -> None:
        self.assertEqual(
            normalize_sf_path("/home/user/repo/src/orders.py", "/home/user/repo"),
            "src/orders.py",
        )

    def test_relative_path_kept_as_is(self) -> None:
        self.assertEqual(normalize_sf_path("src/orders.py", "/repo"), "src/orders.py")

    def test_absolute_outside_root_kept(self) -> None:
        self.assertEqual(
            normalize_sf_path("/elsewhere/x.py", "/home/user/repo"), "/elsewhere/x.py"
        )

    def test_path_equal_to_root(self) -> None:
        self.assertEqual(normalize_sf_path("/repo", "/repo/"), "")


class IsExcludedTest(unittest.TestCase):
    """Default and user-supplied coverage exclusions."""

    def test_tests_segment(self) -> None:
        self.assertTrue(is_excluded("tests/test_orders.py", []))
        self.assertTrue(is_excluded("pkg/tests/helpers.py", []))

    def test_test_basenames(self) -> None:
        for path in (
            "src/app/test_orders.py",
            "src/app/orders_test.py",
            "src/app/conftest.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_excluded(path, []))

    def test_production_file_not_excluded(self) -> None:
        self.assertFalse(is_excluded("src/app/orders.py", []))
        self.assertFalse(is_excluded("src/app/attests.py", []))
        self.assertFalse(is_excluded("src/app/latest_config.py", []))

    def test_user_glob_against_path_and_basename(self) -> None:
        self.assertTrue(is_excluded("src/generated/schema.py", ["src/generated/*"]))
        self.assertTrue(is_excluded("src/deep/nested/schema.py", ["schema.py"]))
        self.assertFalse(is_excluded("src/app/orders.py", ["src/generated/*"]))


class MutationScopeEmptyTest(unittest.TestCase):
    """Scope-emptiness predicate that drives the mutation short-circuit."""

    def test_empty_added_set(self) -> None:
        self.assertEqual(mutation_scope_empty({}, []), (True, False))

    def test_test_only_additions(self) -> None:
        added = {"tests/test_orders.py": {1, 2}, "src/app/conftest.py": {3}}
        self.assertEqual(mutation_scope_empty(added, []), (True, False))

    def test_non_python_additions(self) -> None:
        added = {"README.md": {1}, "src/App/Order.cs": {2}}
        self.assertEqual(mutation_scope_empty(added, []), (True, False))

    def test_user_globs_emptied_the_scope(self) -> None:
        added = {"src/generated/schema.py": {1}}
        self.assertEqual(mutation_scope_empty(added, ["src/generated/*"]), (True, True))

    def test_mixed_scope_is_not_empty(self) -> None:
        added = {"src/app/orders.py": {1}, "tests/test_orders.py": {2}}
        self.assertEqual(mutation_scope_empty(added, []), (False, False))


class IntersectTest(unittest.TestCase):
    """Added-lines-versus-lcov intersection with the counted-uncovered rule."""

    def test_covered_uncovered_and_noncoverable_lines(self) -> None:
        report = intersect(
            {"src/app/orders.py": {1, 2, 3}},
            {"src/app/orders.py": {1: 1, 2: 0}},
            [],
        )
        self.assertEqual(report.per_file, [("src/app/orders.py", 1, 2)])
        self.assertEqual(report.uncovered, [("src/app/orders.py", 2)])
        self.assertEqual(report.not_instrumented, [])
        self.assertEqual((report.total_covered, report.total_coverable), (1, 2))

    def test_non_python_and_excluded_files_skipped(self) -> None:
        report = intersect(
            {"README.md": {5}, "tests/test_it.py": {1}},
            {},
            [],
        )
        self.assertEqual(report, CoverageReport())

    def test_all_uninstrumented_diff_counts_fully_uncovered(self) -> None:
        report = intersect({"src/app/new_module.py": {1, 2, 3}}, {}, [])
        self.assertEqual(report.not_instrumented, [("src/app/new_module.py", 3)])
        self.assertEqual(report.per_file, [])
        self.assertEqual((report.total_covered, report.total_coverable), (0, 3))

    def test_uninstrumented_file_drags_instrumented_sibling_ratio(self) -> None:
        report = intersect(
            {"src/app/old.py": {1, 2}, "src/app/new_module.py": {1, 2}},
            {"src/app/old.py": {1: 1, 2: 1}},
            [],
        )
        self.assertEqual(report.per_file, [("src/app/old.py", 2, 2)])
        self.assertEqual(report.not_instrumented, [("src/app/new_module.py", 2)])
        self.assertEqual((report.total_covered, report.total_coverable), (2, 4))

    def test_instrumented_file_with_no_coverable_added_lines(self) -> None:
        report = intersect({"src/app/doc.py": {5}}, {"src/app/doc.py": {1: 1}}, [])
        self.assertEqual(report, CoverageReport())


class TomlBasicStringTest(unittest.TestCase):
    """TOML basic-string escaping and control-character rejection."""

    def test_plain_value_quoted(self) -> None:
        self.assertEqual(toml_basic_string("src"), '"src"')

    def test_embedded_double_quote_escaped(self) -> None:
        self.assertEqual(toml_basic_string('a"b'), '"a\\"b"')

    def test_embedded_backslash_escaped(self) -> None:
        self.assertEqual(toml_basic_string("a\\b"), '"a\\\\b"')

    def test_embedded_newline_rejected_as_usage_error(self) -> None:
        with self.assertRaises(GateError) as ctx:
            toml_basic_string('src"\nextra = "injected')
        self.assertEqual(ctx.exception.code, EXIT_USAGE)

    def test_other_control_characters_rejected(self) -> None:
        for value in ("a\tb", "a\x1bb", "a\x7fb"):
            with self.subTest(value=value):
                with self.assertRaises(GateError) as ctx:
                    toml_basic_string(value)
                self.assertEqual(ctx.exception.code, EXIT_USAGE)


class BuildCosmicRayConfigTest(unittest.TestCase):
    """Config generation, round-tripped through ``tomllib`` where available."""

    @unittest.skipUnless(sys.version_info >= (3, 11), "tomllib requires Python 3.11")
    def test_round_trip_plain_values(self) -> None:
        text = build_cosmic_ray_config("src", "python -m pytest", 300.0, "abc123")
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["cosmic-ray"]["module-path"], "src")
        self.assertEqual(parsed["cosmic-ray"]["test-command"], "python -m pytest")
        self.assertEqual(parsed["cosmic-ray"]["timeout"], 300.0)
        self.assertEqual(parsed["cosmic-ray"]["excluded-modules"], [])
        self.assertEqual(parsed["cosmic-ray"]["distributor"]["name"], "local")
        self.assertEqual(
            parsed["cosmic-ray"]["filters"]["git-filter"]["branch"], "abc123"
        )

    @unittest.skipUnless(sys.version_info >= (3, 11), "tomllib requires Python 3.11")
    def test_round_trip_hostile_values(self) -> None:
        module_path = 'src"] evil'
        test_command = 'pytest -k "a\\b"'
        text = build_cosmic_ray_config(module_path, test_command, 42.5, "abc123")
        parsed = tomllib.loads(text)
        self.assertEqual(parsed["cosmic-ray"]["module-path"], module_path)
        self.assertEqual(parsed["cosmic-ray"]["test-command"], test_command)

    def test_newline_in_value_rejected_as_usage_error(self) -> None:
        with self.assertRaises(GateError) as ctx:
            build_cosmic_ray_config("src", 'x"\n[evil]\ny = "z', 300.0, "abc123")
        self.assertEqual(ctx.exception.code, EXIT_USAGE)


class ParseSurvivalRateTest(unittest.TestCase):
    """Verdict-versus-crash discrimination over ``cr-rate`` output.

    The bare-number samples are real cosmic-ray 8.7.0 output, captured from a
    probe run; that version prints exactly one ``{rate:.2f}`` line.
    """

    def test_bare_rate_line_with_survivors(self) -> None:
        self.assertEqual(parse_survival_rate("50.00\n"), 50.0)

    def test_bare_zero_rate_line(self) -> None:
        self.assertEqual(parse_survival_rate("0.00\n"), 0.0)

    def test_percent_marked_number(self) -> None:
        self.assertEqual(parse_survival_rate("survival: 20.00%\n"), 20.0)

    def test_rate_line_without_percent_sign(self) -> None:
        self.assertEqual(parse_survival_rate("survival rate: 12.5\n"), 12.5)

    def test_traceback_has_no_rate(self) -> None:
        text = (
            "Traceback (most recent call last):\n"
            '  File "cr_rate.py", line 42, in main\n'
            "KeyError: 'session'\n"
        )
        self.assertIsNone(parse_survival_rate(text))

    def test_empty_output_has_no_rate(self) -> None:
        self.assertIsNone(parse_survival_rate(""))


class FilesOutsideModulePathTest(unittest.TestCase):
    """Guard against the all-skipped false pass on a module-path mismatch."""

    def test_all_files_under_module_path(self) -> None:
        paths = ["src/app/orders.py", "src/app/users.py"]
        self.assertEqual(files_outside_module_path(paths, "src"), [])

    def test_some_files_outside(self) -> None:
        paths = ["src/app/orders.py", "scripts/tool.py"]
        self.assertEqual(files_outside_module_path(paths, "src"), ["scripts/tool.py"])

    def test_all_files_outside(self) -> None:
        paths = ["scripts/tool.py", "lib/util.py"]
        self.assertEqual(files_outside_module_path(paths, "src"), paths)

    def test_module_path_as_single_file(self) -> None:
        self.assertEqual(files_outside_module_path(["src/app.py"], "src/app.py"), [])

    def test_similar_prefix_is_outside(self) -> None:
        self.assertEqual(
            files_outside_module_path(["src2/app.py"], "src"), ["src2/app.py"]
        )

    def test_dot_module_path_covers_everything(self) -> None:
        self.assertEqual(files_outside_module_path(["anything.py"], "."), [])


class ParseArgsTest(unittest.TestCase):
    """CLI parsing, with usage errors remapped to exit 64."""

    def test_defaults(self) -> None:
        args = parse_args([])
        self.assertEqual(args.cov_threshold, 80)
        self.assertEqual(args.module_path, "src")
        self.assertEqual(args.timeout, 300.0)
        self.assertTrue(args.test_command.endswith(" -m pytest"))

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
        for flag in ("--lcov-file", "--module-path"):
            with self.subTest(flag=flag):
                with (
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as ctx,
                ):
                    parse_args([flag, "--evil"])
                self.assertEqual(ctx.exception.code, 64)

    def test_non_positive_timeout_exits_64(self) -> None:
        for bad in ("0", "-5", "abc"):
            with self.subTest(value=bad):
                with (
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as ctx,
                ):
                    parse_args(["--timeout", bad])
                self.assertEqual(ctx.exception.code, 64)


class ParseDiffFileStatusTest(unittest.TestCase):
    """New / pre-existing / rename classification from diff headers."""

    def test_new_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app/new.py b/src/app/new.py
            new file mode 100644
            index 0000000..1111111
            --- /dev/null
            +++ b/src/app/new.py
            @@ -0,0 +1,2 @@
            +def a(): ...
            +def b(): ...
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {"src/app/new.py": (True, "src/app/new.py")})

    def test_modified_file(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/app/mod.py b/src/app/mod.py
            index 1111111..2222222 100644
            --- a/src/app/mod.py
            +++ b/src/app/mod.py
            @@ -3 +3 @@
            -old
            +new
            """
        )
        self.assertEqual(
            parse_diff_file_status(diff), {"src/app/mod.py": (False, "src/app/mod.py")}
        )

    def test_rename_with_edits_keeps_old_path(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old.py b/src/new.py
            similarity index 90%
            rename from src/old.py
            rename to src/new.py
            index 1111111..2222222 100644
            --- a/src/old.py
            +++ b/src/new.py
            @@ -10,0 +11 @@
            +def added(): ...
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {"src/new.py": (False, "src/old.py")})

    def test_pure_rename_no_hunk(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/old.py b/src/new.py
            similarity index 100%
            rename from src/old.py
            rename to src/new.py
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {"src/new.py": (False, "src/old.py")})

    def test_deletion_contributes_nothing(self) -> None:
        diff = textwrap.dedent(
            """\
            diff --git a/src/gone.py b/src/gone.py
            deleted file mode 100644
            index 1111111..0000000
            --- a/src/gone.py
            +++ /dev/null
            @@ -1,2 +0,0 @@
            -a
            -b
            """
        )
        self.assertEqual(parse_diff_file_status(diff), {})


class IsSizeTestFileTest(unittest.TestCase):
    """Test-file classification for the size gate (warn-only set)."""

    def test_tests_segment_and_basenames(self) -> None:
        for path in (
            "tests/test_orders.py",
            "pkg/tests/helpers.py",
            "src/app/test_orders.py",
            "src/app/orders_test.py",
            "src/app/conftest.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_size_test_file(path))

    def test_production_files_not_test(self) -> None:
        for path in ("src/app/orders.py", "src/app/latest_config.py", "src/app/attests.py"):
            with self.subTest(path=path):
                self.assertFalse(is_size_test_file(path))


class IsSizeSkippedTest(unittest.TestCase):
    """The gate scripts skip by default; user --exclude globs skip more."""

    def test_ordinary_files_not_skipped(self) -> None:
        self.assertFalse(is_size_skipped("src/app/orders.py", []))
        self.assertFalse(is_size_skipped("tests/test_orders.py", []))

    def test_gate_scripts_skipped_by_default(self) -> None:
        self.assertTrue(is_size_skipped("skills/python/scripts/python_quality_gate.py", []))
        self.assertTrue(is_size_skipped("skills/rust/scripts/rust_quality_gate.py", []))
        self.assertTrue(is_size_skipped("skills/csharp/scripts/csharp_quality_gate.py", []))

    def test_user_glob_against_path_and_basename(self) -> None:
        self.assertTrue(is_size_skipped("src/generated/schema.py", ["src/generated/*"]))
        self.assertTrue(is_size_skipped("src/deep/nested/schema.py", ["schema.py"]))
        self.assertFalse(is_size_skipped("src/app/orders.py", ["src/generated/*"]))


class SizeVerdictTest(unittest.TestCase):
    """The size policy decision, warn 800 / cap 1500 / allowance 50."""

    def verdict(self, counted, is_new, base, is_test=False):
        return size_verdict(counted, is_new, base, is_test, 800, 1500, 50)

    def test_new_below_warn_is_ok(self) -> None:
        self.assertEqual(self.verdict(799, True, None), "OK")

    def test_new_at_warn_is_warn(self) -> None:
        self.assertEqual(self.verdict(800, True, None), "WARN")

    def test_new_at_cap_is_fail(self) -> None:
        self.assertEqual(self.verdict(1500, True, None), "FAIL")

    def test_new_test_file_at_cap_downgrades_to_warn(self) -> None:
        self.assertEqual(self.verdict(1600, True, None, is_test=True), "WARN")

    def test_preexisting_under_cap_crossing_fails(self) -> None:
        self.assertEqual(self.verdict(1500, False, 1400), "FAIL")

    def test_preexisting_grew_past_allowance_into_warn(self) -> None:
        self.assertEqual(self.verdict(900, False, 800), "WARN")

    def test_preexisting_small_growth_is_ok(self) -> None:
        self.assertEqual(self.verdict(840, False, 800), "OK")

    def test_preexisting_grew_but_below_warn_is_ok(self) -> None:
        self.assertEqual(self.verdict(700, False, 600), "OK")

    def test_preexisting_already_over_cap_grew_warns(self) -> None:
        self.assertEqual(self.verdict(1700, False, 1600), "WARN")

    def test_preexisting_already_over_cap_tiny_growth_is_ok(self) -> None:
        self.assertEqual(self.verdict(1610, False, 1600), "OK")

    def test_preexisting_already_over_cap_never_fails(self) -> None:
        self.assertNotEqual(self.verdict(3000, False, 1600), "FAIL")


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


class StripControlTest(unittest.TestCase):
    """Sanitization of source lines echoed into the report."""

    def test_ansi_sequences_removed(self) -> None:
        self.assertEqual(strip_control("\x1b[31mred\x1b[0m text"), "red text")

    def test_control_characters_removed_tab_kept(self) -> None:
        self.assertEqual(strip_control("a\x07b\tc\x00d"), "ab\tcd")


if __name__ == "__main__":
    unittest.main()
