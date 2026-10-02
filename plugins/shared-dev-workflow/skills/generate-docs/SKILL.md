---
name: generate-docs
description: Write code documentation (JSDoc for JS/TS, docstrings for Python) and project documentation (README.md / docs/**) for the files changed on the current branch, matching the project's existing style. Use when the user asks to document changes, add JSDoc or docstrings, update the README for a change, get a branch ready for a PR, or invokes /generate-docs.
---

# Generate documentation for changed files

Brings the current branch in line with two documentation rules (rules 4 and 5 of the
`setup-pr-policy` PR policy, if the project uses it):

- **Code documentation:** every public/exported declaration in a changed source file has
  documentation appropriate to the language (JSDoc for JS/TS, docstrings for Python).
- **Project documentation:** a change to source files comes with a matching update to
  `README.md` (or `docs/**`).

Project-specific rules in `CLAUDE.md` override the defaults here.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Source files** for code docs: include languages present in the change set. Typical globs:
  - JS/TS: `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`
  - Python: `.py`
  - Other project languages that appear in the diff when the repo clearly documents them
  Under the project's source directories (usually `src/` or a Python package root; check
  `PR_SOURCE_DIRS` in the `check:pr` script if there is one). Skip tests, type stubs
  (`.d.ts`, `*_pb2.py`), and generated files.
- **The full list** is for deciding what the README needs.
- If no source files changed, say so and stop.

## 2. Understand what changed

For each source file:

- Read the whole file, and its diff (`git diff --merge-base <base> -- <file>`), to see what is
  new or different.
- Read its direct imports enough to describe parameters, return values, and thrown/raised
  errors accurately. Don't guess at behavior. If a function's intent is unclear, say so instead
  of inventing documentation.

## 3. Update the project documentation (language-neutral)

Read `README.md`, and `docs/` if it exists, then update every section the change affects. Use
the README's own section names. The common cases:

| Change in the branch                                           | Where to document it                                 |
| -------------------------------------------------------------- | ---------------------------------------------------- |
| New or changed command, flag, API, or user-visible behavior    | Features / Usage / API section                       |
| Added, removed, or renamed files or directories                | Project structure tree or file list, if the README has one |
| New module or layer, or a change in how components interact    | Architecture section                                 |
| New configuration, environment variable, or setup step         | Installation / Configuration section                 |
| Test tooling, conventions, or scripts changed                  | Testing / Contributing section                       |
| New `package.json` script or project CLI entry                 | The section that lists commands                      |

- Keep the README's tone and formatting.
- Describe what the code does now, not what the PR did. The README isn't a changelog. Update
  `CHANGELOG.md` only if the project keeps one.
- If a topic would make the README unwieldy, put it in `docs/<topic>.md` and link to it from
  the README.
- If a change truly has no user- or contributor-visible effect (for example, an internal
  refactor), make the smallest accurate update, such as fixing a renamed file in the structure
  tree. If nothing in the docs is affected, tell the user rather than padding the docs to pass
  a check.

## 4. Write code docs (language-aware)

For each changed source file, match the project's existing comment/docstring style. Defaults
below apply only when the file (and nearby files) don't already establish one.

### JS/TS — JSDoc

**Required:** every top-level `export function | class | const | let | interface | type | enum`
(also with `default`, `async`, or `abstract`). Re-exports (`export * from`, `export { ... }`)
don't need comments.

**Encouraged, not enforced:** public class methods, and non-trivial internal helpers when the
file already documents its helpers.

**Style:** find a well-documented file in the project and match it. Without one, use this shape:

```ts
/**
 * Checks whether a package version meets or exceeds the required version.
 *
 * A single leading `v` and any build metadata (`+...`) are ignored, and missing
 * components are treated as zero, so `1.2` is equivalent to `1.2.0`.
 *
 * @param packageVersion The installed package version.
 * @param requiredVersion The minimum version required.
 * @returns `true` if `packageVersion` is greater than or equal to `requiredVersion`.
 * @throws {VersionError} When either version can't be parsed.
 */
```

Conventions:

- **Summary:** start with one summary sentence in the present tense ("Checks…", "Returns…").
  Add a paragraph only for what a caller needs and can't see in the signature: edge cases,
  normalization, side effects such as I/O, logging, or spawning processes.
- **`@param`:** `@param name Description.` for each parameter, in order. In TypeScript, leave
  out `{type}` because the compiler supplies it. In plain JavaScript, include `{type}` if the
  project uses JSDoc for type checking.
- **`@returns`:** for functions that return a value. For `Promise<void>`, describe what
  completing means only when that isn't obvious.
- **`@throws {ErrorClass} When…`:** for every error that can escape the function. Leave it out
  when the function catches and handles errors itself.
- **Classes and constants:** classes get a summary of what they represent. Constants get one
  line saying what the value is and where it's used.
- **Placement and format:** put the comment directly above the declaration, with no blank line
  in between. Match the file's indentation and line width.
- **Comments only:** never change code while documenting it. If you spot a bug, report it to
  the user instead.
- **No restating:** don't add comments that only repeat the name (`/** The logger. */`).

### Python — docstrings

**Required:** module docstring when the file is a public package module; every public
function, class, and public method. Skip private names (leading `_`) unless the project
already documents them, and skip `__all__` re-exports that only re-export documented names.

**Style:** match an existing well-documented module. Without one, use **Google style**. Switch
to NumPy or Sphinx only when the repo already uses that style.

```python
def meets_required_version(package_version: str, required_version: str) -> bool:
    """Check whether a package version meets or exceeds the required version.

    A single leading ``v`` and any build metadata (``+...``) are ignored, and
    missing components are treated as zero, so ``1.2`` is equivalent to ``1.2.0``.

    Args:
        package_version: The installed package version.
        required_version: The minimum version required.

    Returns:
        ``True`` if ``package_version`` is greater than or equal to
        ``required_version``.

    Raises:
        VersionError: When either version can't be parsed.
    """
```

Conventions:

- **Summary:** one present-tense sentence (or imperative for modules/classes describing what
  they provide). Add a blank line and further paragraphs only for caller-visible behavior.
- **Args / Returns / Raises:** include each parameter, the return value when non-`None`/non-
  obvious, and every exception that can escape. Omit sections the project style leaves empty.
- **Placement:** module docstring is the first statement; others sit immediately under the
  `def` / `class` line (or under the signature for multi-line defs).
- **Docstrings only:** never change code while documenting it. If you spot a bug, report it.
- **No restating:** don't add docstrings that only repeat the name.

### Other / unclear languages

Ask the user which documentation convention to use, or skip code docs for those files and still
complete project documentation (step 3) when needed. Don't invent a style for an unfamiliar
language without confirmation.

## 5. Verify before handing back

- If the project has a `check:pr` script, run it (with the base ref if it isn't the default).
  Treat JSDoc failures as TypeScript/JavaScript project checks. Confirm that no
  `missing a JSDoc comment` or `no documentation was updated` failures remain. Report other
  failures (TODOs, coverage) to the user.
- For coverage gaps, suggest `/typescript-dev-workflow:generate-jest-tests` or
  `/python-dev-workflow:generate-pytest-tests` as appropriate to the changed languages.
- Run the project's lint script (and any docstring/type-check tooling the project already uses)
  to make sure nothing broke.
- Report which declarations you documented, which doc sections you changed, and anything you
  couldn't document confidently.
