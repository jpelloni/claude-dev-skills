---
name: review-dependencies
description: Review changed npm, pnpm, yarn, and Python dependency manifests and lockfiles for lockfile drift, new install scripts, git or file dependencies, and unpinned ranges where the project pins. Report ranked findings. Apply patches only when the user asks. Do not query a vulnerability database or invent CVEs. Use when the user asks to review dependencies, a lockfile, package.json, pyproject, or requirements, or invokes /review-dependencies.
---

# Review dependencies

Reviews dependency manifests and lockfiles in the repository and produces a ranked findings
report. Scope is files on disk — no install, no audit command, no vulnerability database.
Project-specific rules in `CLAUDE.md` or the existing dependency section of the README
always override the defaults here.

**Do not auto-apply patches.** Propose a manifest diff, then ask before writing files.
Never silently change a dependency.

**Do not invent a version, a checksum, or a CVE.** Cite a version or integrity hash only
when it is already in the repo. If a pin is missing, say the user has to choose it. Do not
call npm audit, pip-audit, OSV, or any other advisory service, and do not report a
vulnerability you did not read in the tree.

**Do not invent an ecosystem.** Review the package manager the repo already uses. If the
change only touches `go.mod`, `Cargo.toml`, or another ecosystem, say this skill covers
npm, pnpm, yarn, and Python, and stop.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Include** manifests and lockfiles from that set (or from the user-named scope):
  - npm / pnpm / yarn: `package.json`, `package-lock.json`, `npm-shrinkwrap.json`,
    `pnpm-lock.yaml`, `yarn.lock`, and `.npmrc` when it sets a registry.
  - Python: `pyproject.toml`, `poetry.lock`, `uv.lock`, `pdm.lock`, `Pipfile`,
    `Pipfile.lock`, `requirements*.txt`, `requirements.in`, `requirements/*.txt`,
    `requirements/*.in`, and `setup.cfg` / `setup.py` only for `install_requires`.
- When a manifest changes, also read the lockfile the project uses even if that lockfile
  is unchanged. When a specifier is `file:`, `link:`, or a path, read that package's
  manifest inside the repo even if the user did not name it.
- Read the whole manifest, not only the diff hunk. Direct dependencies are the ones in
  `dependencies`, `devDependencies`, `optionalDependencies`, `peerDependencies`,
  Poetry/uv dependency tables, `Pipfile` packages, `install_requires`, and requirement lines.
  Transitive entries matter only when they add an install script or change registry host.
- Skip application source, tests, and docs unless the user names them.
- If the change has no manifest and no lockfile, say so and stop.

## 2. Learn the dependency rules

Read these before scoring findings:

- **Project rules:** `CLAUDE.md` and any README / `docs/**` section on dependencies, pinning,
  or the package manager. Note whether direct dependencies must be exact versions and which
  lockfile is required.
- **Package manager:** `packageManager` in `package.json`, the lockfile that exists, or the
  tool named in `CLAUDE.md`. Do not assume npm when `pnpm-lock.yaml` or `uv.lock` is the
  file the repo commits.
- **One existing direct dependency** that already matches the rules (an exact pin recorded
  in the lockfile). Match that style in suggested patches.
- Prefer project rules over generic pinning advice when they conflict.

## 3. Analyze each target

Rank each finding **critical**, **warn**, or **note**. Quote the specifier or script you
can see. If a `file:` or path target is outside the repo, say you could not read its
manifest instead of guessing what it runs.

### Install scripts

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| New or changed `preinstall`, `install`, `postinstall`, or `prepare` on the root package, or on a `file:` / path package this change adds | critical | The package manager runs it on install, before tests |
| A `file:` or path dependency whose manifest you cannot read | warn | The install script would be invisible. Say which path is missing |
| `test`, `build`, `start`, or `lint` scripts | do not flag | They do not run on install |

### Lockfile drift

Apply this only when the repo already commits a lockfile, or `CLAUDE.md` requires one.
A project that has never committed a lockfile gets one note for the review, not a finding
per dependency.

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| A direct dependency added, removed, or given a new specifier, and the project's lockfile has no matching entry | critical | The install is not the tree you reviewed |
| `requirements.in` (or another pip-tools input) changed and the compiled `requirements.txt` does not contain the new pin | critical | The committed requirements are stale |
| Lockfile updated and every direct specifier still matches | do not flag | Transitive refresh alone is not drift |
| No lockfile, and the project has never had one | one note for the whole review | Do not demand a lockfile the repo does not use |

The npm lockfile records a direct dependency when `packages[""]` lists it and
`packages["node_modules/<name>"]` exists (`node_modules/@scope/name` for a scoped name).
pnpm and Poetry/uv record it under that dependency's name. A Yarn classic lockfile records
it as a key. Quote the missing name; do not paste the whole lockfile.

### Unpinned ranges

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `*`, `latest`, `x`, an empty specifier, `>=` with no upper bound, or a Python requirement with no `==` / compatible pin | warn when other direct dependencies in the same file are exact pins | The next install can move. Critical only when the lockfile also lacks an entry — report that once, under drift, and keep the range at warn |
| `^` or `~` | do not flag when the project already uses ranges and the lockfile records a resolved version | A range plus a lockfile is the normal npm layout. Warn only when `CLAUDE.md` or the rest of the manifest requires exact versions |
| An exact version that matches the lockfile entry | do not flag | This is the pinned case |

### Git, URL, and file dependencies

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `git+`, `git://`, `github:`, `gitlab:`, `bitbucket:`, an `http(s)` tarball, `file:`, or `link:` | warn | The package skips the registry the lockfile was built from. Critical when that in-repo target has an install script (score it once, as the script) |
| Python VCS URL (`@ git+...`) or path dependency | warn | Same as a git or `file:` specifier |
| New `--index-url`, `--extra-index-url`, Poetry or uv source, or `.npmrc` `registry` whose host is not already used in the lockfile or named in `CLAUDE.md` | warn | Install can resolve a different package of the same name. Do not flag `registry.npmjs.org` or `pypi.org` |

### What not to flag

- A caret or tilde range when the lockfile records a resolved version and the project already uses ranges.
- Moving a package between `dependencies` and `devDependencies`.
- A transitive lockfile bump where every direct specifier is unchanged and no install script was added.
- A missing CVE, advisory, or audit report.
- A comment that disagrees with the specifier. Review the specifier.

**Out of scope:** running the package manager, querying a vulnerability database, fabricating
a lockfile or integrity hash, Dockerfiles, and GitHub Actions.

## 4. Report findings

Produce a ranked report. For each finding include:

1. **Location** — file path and the specifier or script (`banner-cli: "*"`,
   `scripts.postinstall`).
2. **Severity** — critical / warn / note.
3. **Why it hurts** — one or two sentences.
4. **Tighter alternative** — the pin or script change that matches the project rule. For a
   missing lockfile entry, the alternative is to regenerate with the package manager the
   repo already uses. Name that command. Do not write lockfile JSON or a hash by hand. For
   an unpinned range, cite a version already in the lockfile, or say the user has to choose
   one. Do not invent one.

Group by severity (critical first). Name the package manager and lockfile in one line at the top.

## 5. Suggest patches (ask before applying)

- Propose the manifest edit only. Ask the user which findings to apply. Write files only
  for the ones they confirm.
- Do not regenerate a lockfile unless the user asks. If they ask, use the package manager
  the repo already uses, then re-read the lockfile and confirm each direct dependency is
  recorded. Do not hand-edit integrity hashes.
- Removing an install script does not remove the package. Say so, and do not uninstall it
  unless the user asks.

## 6. Hand back

Summarize:

- Counts by severity (critical / warn / note).
- Files reviewed; files changed only if patches were applied.
- Package manager and lockfile assumed, and any `file:` or path manifest you could not read.
- Remind that this review does not query a vulnerability database and does not run an install.
