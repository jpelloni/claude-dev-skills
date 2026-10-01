// Enforces the pull request rules on files changed relative to a base ref:
//   1. No TODO comments remain in changed source or test files.
//   2. Every changed source file has >= COVERAGE_THRESHOLD% coverage
//      (lines, statements, functions, and branches).
//   3. Every exported declaration in a changed source file has a JSDoc
//      (/** ... */) comment directly above it.
//   4. A PR that changes source files also updates project documentation
//      (README.md or docs/**).
//
// Changed files include uncommitted and untracked work, so this can be run
// locally before committing.
//
// Run the test suite with a json-summary coverage reporter first (`test:pr`).
// Usage: node scripts/check-pr.mjs [base-ref]   (default: origin's default branch)
//
// Configuration (environment variables):
//   COVERAGE_THRESHOLD  minimum coverage percentage            (default: 80)
//   COVERAGE_SUMMARY    path to the json-summary report        (default: coverage/coverage-summary.json)
//   PR_SOURCE_DIRS      comma-separated source directories     (default: src)
//   PR_TEST_DIRS        comma-separated test directories       (default: tests)
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const list = (value, fallback) => (value ?? fallback).split(',').map((dir) => dir.trim().replace(/\/+$/, '')).filter(Boolean);

const git = (...args) => execFileSync('git', args, { encoding: 'utf8' })
    .split('\n')
    .map((file) => file.trim())
    .filter(Boolean);

const defaultBaseRef = () => {
    try {
        return git('symbolic-ref', '--short', 'refs/remotes/origin/HEAD')[0];
    } catch {
        return 'origin/main';
    }
};

const baseRef = process.argv[2] ?? process.env.BASE_REF ?? defaultBaseRef();
const threshold = Number(process.env.COVERAGE_THRESHOLD ?? 80);
const summaryPath = path.resolve(process.env.COVERAGE_SUMMARY ?? 'coverage/coverage-summary.json');
const sourceDirs = list(process.env.PR_SOURCE_DIRS, 'src');
const testDirs = list(process.env.PR_TEST_DIRS, 'tests');
const metrics = ['lines', 'statements', 'functions', 'branches'];
const todoPattern = /\bTODO\b/i;
// Exported declarations that need JSDoc. Re-exports (`export * from`, `export { ... }`) are excluded.
const exportPattern = /^export\s+(?:default\s+)?(?:declare\s+)?(?:async\s+)?(?:abstract\s+)?(?:function\*?|class|const|let|var|interface|type|enum)\s+(\w+)/;
const codePattern = /\.(?:[cm]?[jt]s|[jt]sx)$/;
const testFilePattern = /\.(?:test|spec)\.[^.]+$/;
const docPattern = /^(README\.md|docs\/.+)$/;

const inDirs = (file, dirs) => dirs.some((dir) => file.startsWith(`${dir}/`));

const changedFiles = [...new Set([
    ...git('diff', '--name-only', '--diff-filter=ACMR', '--merge-base', baseRef),
    ...git('ls-files', '--others', '--exclude-standard'),
])];

const changedCode = changedFiles.filter((f) => codePattern.test(f) && inDirs(f, [...sourceDirs, ...testDirs]));
const changedSources = changedCode.filter((f) => inDirs(f, sourceDirs) && !testFilePattern.test(f) && !f.endsWith('.d.ts'));

const failures = [];

for (const file of changedCode) {
    readFileSync(file, 'utf8')
        .split('\n')
        .forEach((line, index) => {
            if (todoPattern.test(line)) {
                failures.push(`${file}:${index + 1}: unresolved TODO -> ${line.trim()}`);
            }
        });
}

for (const file of changedSources) {
    const lines = readFileSync(file, 'utf8').split('\n');

    lines.forEach((line, index) => {
        const match = exportPattern.exec(line);
        if (!match) return;

        let prev = index - 1;
        while (prev >= 0 && lines[prev].trim() === '') prev--;

        let start = prev;
        while (start >= 0 && !lines[start].includes('/*')) start--;

        const hasJsDoc = prev >= 0 && lines[prev].trim().endsWith('*/') && start >= 0 && lines[start].trim().startsWith('/**');
        if (!hasJsDoc) {
            failures.push(`${file}:${index + 1}: exported \`${match[1]}\` is missing a JSDoc comment`);
        }
    });
}

if (changedSources.length > 0 && !changedFiles.some((f) => docPattern.test(f))) {
    failures.push(`${sourceDirs.join(', ')} changed but no documentation was updated (README.md or docs/**)`);
}

if (changedSources.length > 0) {
    if (!existsSync(summaryPath)) {
        console.error(`Missing ${summaryPath}. Run the tests with coverage (\`test:pr\`) first.`);
        process.exit(1);
    }

    const summary = JSON.parse(readFileSync(summaryPath, 'utf8'));

    for (const file of changedSources) {
        const entry = summary[path.resolve(file)];

        if (!entry) {
            failures.push(`${file}: 0% coverage (not exercised by any test)`);
            continue;
        }

        for (const metric of metrics) {
            const { pct } = entry[metric];
            if (pct < threshold) {
                failures.push(`${file}: ${metric} coverage ${pct}% is below ${threshold}%`);
            }
        }
    }
}

if (failures.length > 0) {
    console.error(`PR checks failed against ${baseRef}:\n`);
    failures.forEach((failure) => console.error(`  - ${failure}`));
    process.exit(1);
}

console.log(
    `PR checks passed: ${changedFiles.length} changed file(s), ` +
    `${changedSources.length} source file(s) at >= ${threshold}% coverage, no TODOs, code and project docs updated.`,
);
