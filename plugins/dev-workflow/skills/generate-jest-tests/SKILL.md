---
name: generate-jest-tests
description: Generate a full Jest (or Vitest) unit test suite for a JavaScript/TypeScript source file, following the project's own test layout, module system, and conventions, and iterate until it passes with >= 80% coverage. Use when the user asks to write, generate, or scaffold unit tests for a file, raise coverage for a file, or invokes /generate-jest-tests.
---

# Generate unit tests for a source file

Writes a complete, passing unit test suite for one source file, matching how the project already
writes tests. Project-specific rules (in `CLAUDE.md`, the README's testing section, or existing
tests) always override the defaults here.

## 1. Identify the target file

- If the user named a file (or passed one as an argument), use it.
- Otherwise use the file most recently opened or edited in this session.
- If neither is available, ask the user which file to target. Don't guess.
- Confirm the file exists and is source code, not a test, config, or generated file.

## 2. Learn the project's test setup

Read these before writing anything:

- **Project rules:** `CLAUDE.md` and the README's testing or contributing section. They may
  list mocking rules, error classes to assert against, or files that must never be touched.
- **Runner and config:** `jest.config.*` or the `"jest"` key in `package.json`, or
  `vitest.config.*` / `vite.config.*`. Note `roots`, `testMatch`, `transform` (ts-jest,
  babel-jest, @swc/jest), `moduleNameMapper`, `extensionsToTreatAsEsm`, and coverage settings.
- **Scripts:** how `package.json` runs tests (`test`, `test:coverage`, `test:pr`), including any
  flags such as `node --experimental-vm-modules`.
- **One or two existing test files**, preferably near the target. Copy their imports, layout,
  naming, and mocking style. If no tests exist yet, use the defaults below and say so.

## 3. Read before writing

- Read the full target file.
- Read its direct imports enough to know their public signatures. You need these to mock
  correctly.
- Find the existing test file for the target (see step 4). If one exists, extend it rather than
  overwriting working tests.
- If an import doesn't resolve (a renamed or missing module), stop and tell the user rather than
  guessing which module was meant.

## 4. Where the test file goes

Follow the existing layout:

- **Mirrored tree** (for example, `src/a/b.ts` → `tests/a/b.test.ts`): same relative path and
  base filename.
- **Next to the source** (`src/a/b.ts` → `src/a/b.test.ts`) or **`__tests__/` folders**: use
  the same pattern.
- **Suffix:** match the existing `.test` or `.spec` and the file extension.

Make sure the new path matches the runner's `testMatch`/`include` and `roots`. Create
directories as needed.

## 5. Module system and mocking

Work out which mode the project runs in and use the matching pattern.

**CommonJS, or ESM compiled to CommonJS** (babel-jest, or ts-jest without `useESM`):

- `jest.mock('module', factory)` is hoisted above imports, so static imports are fine.

**Native ESM** (`"type": "module"`, ts-jest with `useESM: true`, run with
`node --experimental-vm-modules`):

- `jest` is not a global. Use `const { jest } = import.meta;`, or import from `@jest/globals`
  if the project already depends on it. Don't add the dependency yourself.
- `jest.mock` is not hoisted above static imports. Use
  `jest.unstable_mockModule(specifier, factory)`, then load the mocked module and the module
  under test with `await import(...)` *after* the mock. A static import would bind the real
  module.
- Import paths follow the project's convention, often an explicit `.js` extension that
  `moduleNameMapper` maps back to `.ts`.

**Vitest:** use `vi` from `vitest` (or the globals if `globals: true`). `vi.mock` is hoisted.
Use `vi.hoisted` for values the factory needs.

## 6. What to test

- **Structure:** one top-level `describe` per exported function or class, and one `describe`
  per method for classes. Arrange / Act / Assert in each `it`, one behavior per test.
- **No real side effects:** no real file I/O, process execution, network, or timers. Mock
  `node:child_process`, `node:fs`, HTTP clients, and the project's adapter or gateway modules
  (the boundary to external systems). Use fake timers for time-dependent code.
- **Silence output:** stub or spy on the project's logger (or `console`) so tests don't print.
- **Coverage:** test the happy path, every branch (including `switch`/`default` and early
  returns), and every error path.
- **Errors:** assert the error's class and message, not just that something threw. Use the
  project's custom error classes where they exist.
- **Concurrency:** for functions that run independent operations together (`Promise.all`,
  `allSettled`), test that one failure is handled as designed and doesn't silently abort the
  others.
- **Style:** match the surrounding code (indentation, quotes, semicolons), not your own defaults.

## 7. Verify before handing back

- Run the new or updated test file through the project's test script, for example
  `pnpm test -- path/to/file.test.ts`.
- Check coverage for the target. Aim for >= 80% lines, statements, functions, and branches,
  the bar used by the `setup-pr-policy` check. Run with coverage limited to the target, for
  example `--coverage --collectCoverageFrom=<target>` for Jest.
- Run the project's lint script, and fix violations in the test file (often `no-console`).
- Iterate until the tests pass, coverage is at or above 80%, and lint is clean.
- Report what you added, the coverage you reached, and any gaps, such as code you couldn't test
  safely without more context or that looks unreachable.
