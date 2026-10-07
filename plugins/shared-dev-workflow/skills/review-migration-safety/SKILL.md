---
name: review-migration-safety
description: Review changed database migrations for destructive DDL, missing downgrades, lock-heavy index and column changes, and expand/contract deploy order. Report ranked findings. Apply patches only when the user asks. Use when the user asks to review a migration, Alembic, Django, Prisma, or Flyway change, drop column safety, or invokes /review-migration-safety.
---

# Review migration safety

Reviews database migrations in the repository and produces a ranked findings report.
Scope is files on disk — no live database, no `EXPLAIN`, no applying migrations.
Project-specific rules in `CLAUDE.md` or the existing database section of the README
always override the defaults here.

**Do not auto-apply patches.** Propose a migration diff, then ask before writing files.
Never silently change a migration.

**Do not invent a framework.** Review the tool the repo already uses (Alembic, Django,
Prisma, Flyway, Rails, Liquibase, or raw SQL). If there is no migration in the change,
say so and stop.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Include** migration files from that set (or from the user-named scope):
  - Alembic: `**/versions/*.py` (usually `migrations/versions` or `alembic/versions`).
  - Django: `**/migrations/*.py` except `__init__.py`.
  - Prisma: `prisma/migrations/**/migration.sql`.
  - Flyway / Liquibase: `**/*migration*/**/*.sql`, `V*__*.sql`, `U*__*.sql`, `*.undo.sql`,
    `**/changelog*.xml`, `**/changelog*.yaml`.
  - Rails: `db/migrate/*.rb` and `db/structure.sql` only when a migration in the set changes it.
  - Raw SQL the project keeps under `migrations/`, `migrate/`, or `db/`.
- When a migration's danger depends on readers of a column, search the rest of the change
  for that column name. If the user named only the migration, also search application code
  that is actually in the tree. Finding no readers only counts when you found the code that
  used to read the column and this change removes it.
- Read the whole migration, not only the diff hunk.
- Skip tests, lockfiles, and generated clients unless the user names them.
- If the change has no migration, say so and stop. An ORM model edit with no migration is
  not this review.

## 2. Learn the database rules

Read these before scoring findings:

- **Project rules:** `CLAUDE.md` and any README / `docs/**` section on the database, migrations,
  or deploy order. Note the engine and version, whether downgrades are required, and whether
  indexes on existing tables must be concurrent.
- **Engine:** PostgreSQL, MySQL / MariaDB, SQLite, or unspecified. Apply the locking rules
  for the engine the project names. If it is unspecified, use the PostgreSQL rules, say that
  once, and do not pretend MySQL's automatic foreign-key indexes apply.
- **One peer migration** that already matches the rules (a real `downgrade()`, a concurrent
  index outside a transaction). Match that style in suggested patches.
- Prefer project rules over generic migration advice when they conflict.

## 3. Analyze each target

Rank each finding **critical**, **warn**, or **note**. Quote the operation you can see.
Raw SQL in `op.execute`, `RunSQL`, `migration.sql`, or a `.sql` file counts the same as a
helper call. If a statement is built by a function you have not read, say so instead of
guessing.

### Destructive changes

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `DROP TABLE`, `DROP COLUMN`, `TRUNCATE`, or `DELETE` without a `WHERE` | critical | Data is gone. A failed deploy cannot put it back |
| The same change shows the application stop reading and writing a dropped column | warn | Expand/contract. The application release that stops reading has to deploy before this migration. Say that. No application code in the review is not evidence the column is unused — keep critical |
| `DROP INDEX` that is recreated in the same migration | note | Replacement is present |
| `DROP INDEX` with no replacement | warn | Queries lose the access path. Critical when it was the only uniqueness guarantee |
| `RENAME` of a table or column while this change still reads the old name | critical | The running code breaks as soon as the migration lands |
| `RENAME` whose readers move in the same change, with no compatibility view or dual-write | warn | Code and migration cannot ship as one step. Say which deploy goes first |

### Downgrades

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| Alembic `downgrade()` is `pass`, empty, or `raise NotImplementedError` | warn | The upgrade cannot be reversed. Quote the project rule when it requires a real downgrade. Critical only when the project says a missing downgrade blocks release |
| Django `RunPython` / `RunSQL` with `reverse_code` missing or set to `noop` on a data change | warn | Schema operations Django can reverse on its own are fine. Do not flag those |
| Flyway or raw SQL with no undo script | warn only when this repo already has `U__` or `.undo` scripts; otherwise one note for the review | A project that never undoes migrations is not missing a file on each version |
| Prisma migration with no down script | one note for the whole review, not a finding per file | Prisma migrations are forward-only unless the project has its own down path |

### Locking and rewrites

Apply these to **existing** tables. A migration that only creates a new table, then indexes
it, is empty-table work — do not flag it.

PostgreSQL:

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `ADD COLUMN ... NOT NULL` without a default on an existing table | critical | Existing rows have no value, so PostgreSQL rejects the statement |
| `ADD COLUMN` nullable, or `ADD COLUMN` with a constant (non-volatile) default, including `NOT NULL` plus that default, on PostgreSQL 11+ | do not flag | Metadata-only. A volatile default (`now()`, a function) is a warn: it rewrites the table |
| `ALTER COLUMN ... TYPE`, or a type change that is not binary-compatible | warn | Rewrite plus `AccessExclusiveLock`. Suggest a new column, backfill, then contract |
| `SET NOT NULL` without an existing `NOT VALID` check that already proves the column | warn | Full scan under a lock. Suggest adding a `NOT VALID` check, validating it, then setting not null |
| `CREATE INDEX` on an existing table without `CONCURRENTLY` | warn | Blocks writes for the build. The patch must not put `CONCURRENTLY` inside a transaction |
| `CREATE INDEX CONCURRENTLY` inside a transaction (`upgrade()` with no autocommit block, Django `atomic = True`, Prisma's default migration transaction) | critical | PostgreSQL rejects the statement and the migration fails |
| New `FOREIGN KEY` whose referencing columns are not indexed in this migration | warn | PostgreSQL does not index the referencing side. MySQL does — do not flag MySQL for this |
| New filter or join on a new column, visible in this same change, with no index | warn | Only when you can see both the query and the missing index. Do not invent indexes for columns you did not see queried |

Other engines, briefly:

- **MySQL / MariaDB:** an `ALGORITHM=COPY` alter, or an `ADD COLUMN` / `ADD INDEX` the project
  has already called out as a copy, is warn (table rebuild). Do not apply the PostgreSQL
  constant-default exception unless the project says the server skips the copy.
- **SQLite:** a table rebuild (`ALTER` that copies into a new table) dropping columns is the
  same destructive rule as `DROP COLUMN`.
- **Unspecified:** state that you used the PostgreSQL rules.

### Data movement

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `UPDATE` with no `WHERE` that rewrites every row in the same transaction as DDL | warn | Long transaction, replication lag, and a lock held across the backfill |
| Backfill of a new `NOT NULL` column in a later statement of the same migration, after adding it nullable | note | Right shape, as long as the `SET NOT NULL` is not in this file before the backfill finishes |
| `op.execute` / `RunSQL` whose text you cannot parse | note | Quote it and mark needs-human-review. Do not guess |

### What not to flag

- A nullable column add, or a PostgreSQL 11+ constant-default column add.
- Indexes created only on a table this migration creates.
- A `CONCURRENTLY` index that already runs outside a transaction.
- Prisma's missing down migration, beyond the single note.
- A comment that disagrees with the code. Review the code.

**Out of scope:** connecting to a database, running the migration, `EXPLAIN`, choosing a
framework the repo does not use, and applying patches without confirmation.

## 4. Report findings

Produce a ranked report. For each finding include:

1. **Location** — file path and the operation (`op.drop_column("orders", "legacy_code")`).
2. **Severity** — critical / warn / note.
3. **Why it hurts** — one or two sentences, including deploy order when the change is expand/contract.
4. **Tighter alternative** — the operation that matches the project rule. For a PostgreSQL
   index on an existing table, the alternative is `CREATE INDEX CONCURRENTLY` **outside** a
   transaction. Alembic wraps `upgrade()` in a transaction, so `postgresql_concurrently=True`
   alone is wrong; use `with op.get_context().autocommit_block():` (or the project's existing
   autocommit pattern). Django uses `AddIndexConcurrently` in a migration with `atomic = False`.
   Prisma and default Flyway run inside a transaction: say the concurrent build does not fit
   that file, and do not invent a flag the project does not already use.

Group by severity (critical first). Name the engine you assumed in one line at the top.

## 5. Suggest patches (ask before applying)

- Propose the migration edit only. Ask the user which findings to apply. Write files only
  for the ones they confirm.
- A downgrade must undo what `upgrade()` does, in reverse order, including restoring a
  dropped column as nullable (the data is already gone — say that the downgrade restores
  the schema, not the rows).
- Never silently edit a migration that has already been applied in any environment. If the
  repo treats the file as applied, say the fix belongs in a new migration.

## 6. Hand back

Summarize:

- Counts by severity (critical / warn / note).
- Files reviewed; files changed only if patches were applied.
- Engine assumed, and any statement you could not parse.
- Remind that this review does not connect to a database. A rehearsal against a copy of
  production is a separate step when the user wants one.
