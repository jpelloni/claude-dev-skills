#!/usr/bin/env python3
"""Enforces the pull request rules on files changed relative to a base ref:

1. No TODO comments remain in changed source or test files.
2. Every changed source file has >= COVERAGE_THRESHOLD% line and branch coverage.
3. Every public function, class, and public method in a changed source file has a
   docstring. A module docstring is required when the file defines at least one
   public function or class. Names that start with ``_`` are private.
4. A PR that changes source files also updates project documentation
   (README.md or docs/**).

coverage.py has no separate function-coverage metric, so this checks lines and
branches only. Branch numbers come from a JSON report produced with branch
coverage enabled.

Changed files include uncommitted and untracked work, so this can be run locally
before committing.

Run the test suite with a JSON coverage report first (``test-pr``).
Usage: python scripts/check_pr.py [base-ref]   (default: origin's default branch)

Configuration (environment variables):
  COVERAGE_THRESHOLD  minimum coverage percentage            (default: 80)
  COVERAGE_SUMMARY    path to the coverage.py JSON report    (default: coverage/coverage.json)
  PR_SOURCE_DIRS      comma-separated source directories     (default: src)
  PR_TEST_DIRS        comma-separated test directories       (default: tests)
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TODO_PATTERN = re.compile(r"\bTODO\b", re.IGNORECASE)
TEST_FILE_PATTERN = re.compile(r"(?:^|/)(?:test_[^/]+\.py|[^/]+_test\.py)$")
DOC_PATTERN = re.compile(r"^(?:README\.md|docs/.+)$")


def git(*args: str) -> list[str]:
    result = subprocess.run(["git", *args], check=False, text=True, capture_output=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or f"git {' '.join(args)} failed\n")
        raise SystemExit(1)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def default_base_ref() -> str:
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        check=False,
        text=True,
        capture_output=True,
    )
    ref = result.stdout.strip()
    if result.returncode == 0 and ref:
        return ref
    return "origin/main"


def split_dirs(value: str | None, fallback: str) -> list[str]:
    raw = value if value else fallback
    return [item.strip().strip("/") for item in raw.split(",") if item.strip()]


def in_dirs(path: str, dirs: list[str]) -> bool:
    return any(path == directory or path.startswith(f"{directory}/") for directory in dirs)


def is_test_file(path: str) -> bool:
    return TEST_FILE_PATTERN.search(path) is not None


def is_public(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_")


def docstring_failures(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: {exc}"]

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: syntax error: {exc.msg}"]

    failures: list[str] = []
    if any(is_public(node) for node in tree.body) and not ast.get_docstring(tree):
        failures.append(f"{path}:1: module is missing a docstring")
    failures.extend(missing_docstrings(tree.body, path))
    return failures


def missing_docstrings(body: list[ast.stmt], path: Path) -> list[str]:
    failures: list[str] = []
    for node in body:
        if not is_public(node):
            continue
        if not ast.get_docstring(node):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            failures.append(f"{path}:{node.lineno}: public {kind} `{node.name}` is missing a docstring")
        if isinstance(node, ast.ClassDef):
            failures.extend(missing_docstrings(node.body, path))
    return failures


def load_coverage(summary_path: Path) -> dict:
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Could not read {summary_path}: {exc}\n")
        raise SystemExit(1) from exc
    files = data.get("files")
    if not isinstance(files, dict):
        sys.stderr.write(f"{summary_path} has no coverage.py 'files' object. Run tests with --cov-report=json.\n")
        raise SystemExit(1)
    return files


def coverage_entry(files: dict, relative: str) -> dict | None:
    for key, entry in files.items():
        norm = str(key).replace("\\", "/")
        if norm == relative or norm.endswith("/" + relative):
            return entry
    return None


def line_percent(summary: dict) -> float | None:
    for key in ("percent_statements_covered", "percent_statements", "percent_covered"):
        value = summary.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def branch_percent(summary: dict) -> float | None:
    for key in ("percent_branches_covered", "percent_branches", "percent_covered_branches"):
        value = summary.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    if "num_branches" not in summary:
        return None
    num_branches = summary.get("num_branches")
    if num_branches == 0:
        return 100.0
    covered = summary.get("covered_branches")
    if isinstance(num_branches, int) and isinstance(covered, int) and num_branches > 0:
        return 100.0 * covered / num_branches
    return None


def main() -> None:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BASE_REF") or default_base_ref()
    threshold = float(os.environ.get("COVERAGE_THRESHOLD", "80"))
    summary_path = Path(os.environ.get("COVERAGE_SUMMARY", "coverage/coverage.json")).resolve()
    source_dirs = split_dirs(os.environ.get("PR_SOURCE_DIRS"), "src")
    test_dirs = split_dirs(os.environ.get("PR_TEST_DIRS"), "tests")

    changed = list(dict.fromkeys([
        *git("diff", "--name-only", "--diff-filter=ACMR", "--merge-base", base_ref),
        *git("ls-files", "--others", "--exclude-standard"),
    ]))

    changed_code = [
        path for path in changed
        if path.endswith(".py")
        and not path.endswith("_pb2.py")
        and in_dirs(path, [*source_dirs, *test_dirs])
    ]
    changed_sources = [
        path for path in changed_code
        if in_dirs(path, source_dirs) and not is_test_file(path)
    ]

    failures: list[str] = []

    for path in changed_code:
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            failures.append(f"{path}: {exc}")
            continue
        for index, line in enumerate(lines, start=1):
            if TODO_PATTERN.search(line):
                failures.append(f"{path}:{index}: unresolved TODO -> {line.strip()}")

    for path in changed_sources:
        failures.extend(docstring_failures(Path(path)))

    if changed_sources and not any(DOC_PATTERN.match(path) for path in changed):
        failures.append(
            f"{', '.join(source_dirs)} changed but no documentation was updated (README.md or docs/**)"
        )

    if changed_sources:
        if not summary_path.is_file():
            sys.stderr.write(f"Missing {summary_path}. Run the tests with coverage (`test-pr`) first.\n")
            raise SystemExit(1)
        files = load_coverage(summary_path)
        for path in changed_sources:
            entry = coverage_entry(files, path)
            if entry is None:
                failures.append(f"{path}: 0% coverage (not exercised by any test)")
                continue
            summary = entry.get("summary", {})
            lines_pct = line_percent(summary)
            branches_pct = branch_percent(summary)
            if lines_pct is None:
                failures.append(f"{path}: coverage report has no line percentage")
            elif lines_pct < threshold:
                failures.append(f"{path}: line coverage {lines_pct:.0f}% is below {threshold:.0f}%")
            if branches_pct is None:
                failures.append(f"{path}: branch coverage was not recorded; rerun test-pr with --cov-branch")
            elif branches_pct < threshold:
                failures.append(f"{path}: branch coverage {branches_pct:.0f}% is below {threshold:.0f}%")

    if failures:
        sys.stderr.write(f"PR checks failed against {base_ref}:\n\n")
        for failure in failures:
            sys.stderr.write(f"  - {failure}\n")
        raise SystemExit(1)

    print(
        f"PR checks passed: {len(changed)} changed file(s), "
        f"{len(changed_sources)} source file(s) at >= {threshold:.0f}% line and branch coverage, "
        "no TODOs, code and project docs updated."
    )


if __name__ == "__main__":
    main()
