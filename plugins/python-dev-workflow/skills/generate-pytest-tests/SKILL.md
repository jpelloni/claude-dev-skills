---
name: generate-pytest-tests
description: Generate a full pytest (or unittest) unit test suite for a Python source file, following the project's own test layout, fixtures, and conventions, and iterate until it passes with >= 80% coverage. Use when the user asks to write, generate, or scaffold unit tests for a Python file, raise coverage for a file, or invokes /generate-pytest-tests.
---

# Generate unit tests for a source file

Writes a complete, passing unit test suite for one Python source file, matching how the
project already writes tests. Project-specific rules (in `CLAUDE.md`, the README's testing
section, or existing tests) always override the defaults here.

## 1. Identify the target file

- If the user named a file (or passed one as an argument), use it.
- Otherwise use the file most recently opened or edited in this session.
- If neither is available, ask the user which file to target. Don't guess.
- Confirm the file exists and is source code, not a test, config, or generated file.

## 2. Learn the project's test setup

Read these before writing anything:

- **Project rules:** `CLAUDE.md` and the README's testing or contributing section. They may
  list mocking rules, exception types to assert against, or files that must never be touched.
- **Runner and config:** `pytest.ini`, `pyproject.toml` (`[tool.pytest.ini_options]` /
  `[tool.coverage.*]`), `setup.cfg`, `tox.ini`, or `conftest.py`. Note `testpaths`,
  `python_files`, `python_classes`, `python_functions`, markers, and coverage settings.
- **Scripts / tooling:** how the project runs tests (`pytest`, `python -m pytest`, `tox`,
  `nox`, `make test`, Hatch/Poetry scripts), including any coverage flags such as
  `--cov` / `--cov-report`.
- **One or two existing test files**, preferably near the target. Copy their imports, layout,
  naming, fixtures, and mocking style. If no tests exist yet, use the defaults below and say so.

## 3. Read before writing

- Read the full target file.
- Read its direct imports enough to know their public signatures. You need these to mock
  correctly.
- Find the existing test file for the target (see step 4). If one exists, extend it rather than
  overwriting working tests.
- If an import doesn't resolve (a renamed or missing module), stop and tell the user rather than
  guessing which module was meant. Don't invent missing modules.

## 4. Where the test file goes

Follow the existing layout:

- **Mirrored tree** (for example, `src/pkg/a/b.py` → `tests/pkg/a/test_b.py` or
  `tests/a/test_b.py`): same relative path under the project's test root.
- **Next to the source** (`pkg/a/b.py` → `pkg/a/test_b.py` or `pkg/a/b_test.py`): use the
  same pattern.
- **Naming:** match existing `test_*.py` or `*_test.py` conventions, and whether tests use
  classes (`TestFoo`) or plain functions (`test_foo`).

Make sure the new path matches the runner's `testpaths` / `python_files` discovery rules.
Create directories as needed, including `__init__.py` only if the project already uses them
in the test tree.

## 5. Framework and mocking

Prefer **pytest**. Switch to **unittest** only when the project already uses unittest-style
tests (or clearly documents that as the standard).

**pytest (default):**

- Use plain `assert` (or the project's preferred assertion helpers). Prefer fixtures over
  class setup when that matches nearby tests.
- Put shared fixtures in the nearest existing `conftest.py`, or keep them local if the project
  keeps fixtures per file.
- Mock with `unittest.mock` (`patch`, `MagicMock`, `AsyncMock`) or `pytest-mock`'s `mocker`
  fixture when the project already depends on it. Don't add the dependency yourself.
- Patch where the name is looked up (the importing module), not only where it is defined.
- For async code, follow the project's existing pattern (`pytest-asyncio`, `anyio`, or
  manual event-loop fixtures). Don't introduce a new async plugin if one isn't already used.

**unittest (when that is the project style):**

- Subclass `unittest.TestCase`, use `self.assert*` methods, and put shared setup in
  `setUp` / `tearDown` (or `setUpClass` / `tearDownClass`) as nearby tests do.
- Use `unittest.mock.patch` as a decorator or context manager, matching existing tests.
- Discoverable via `python -m unittest` or whatever script the project already uses.

## 6. What to test

- **Structure:** one test class or grouped section per public function or class, and focused
  tests per method for classes. Arrange / Act / Assert in each test, one behavior per test.
- **No real side effects:** no real file I/O, process execution, network, or clocks. Mock
  `subprocess`, `pathlib`/`open`, HTTP clients, database drivers, and the project's adapter
  or gateway modules (the boundary to external systems). Use freezegun or equivalent only if
  the project already depends on it; otherwise mock time-related calls.
- **Silence output:** stub or spy on the project's logger (or `print` / `logging`) so tests
  don't print.
- **Coverage:** test the happy path, every branch (including `match`/`case` or `if`/`elif`
  chains and early returns), and every error path.
- **Errors:** assert the exception type and message (or attributes), not just that something
  raised. Use the project's custom exception classes where they exist.
- **Concurrency / async:** for functions that run independent operations together
  (`asyncio.gather`, thread pools), test that one failure is handled as designed and doesn't
  silently abort the others.
- **Style:** match the surrounding code (quotes, line length, typing, import order), not your
  own defaults. Prefer the project's formatter/linter settings when present.

## 7. Verify before handing back

- Run the new or updated test file through the project's test script, for example
  `pytest path/to/test_file.py` or `python -m pytest path/to/test_file.py`.
- Check coverage for the target. Aim for >= 80% lines, statements, functions, and branches
  when the tooling reports them. Run with coverage limited to the target, for example
  `pytest --cov=<module.path> --cov-report=term-missing path/to/test_file.py`.
- Run the project's lint or type-check script if one exists for tests, and fix violations in
  the test file.
- Iterate until the tests pass, coverage is at or above 80%, and lint is clean.
- Report what you added, the coverage you reached, and any gaps, such as code you couldn't test
  safely without more context or that looks unreachable.
