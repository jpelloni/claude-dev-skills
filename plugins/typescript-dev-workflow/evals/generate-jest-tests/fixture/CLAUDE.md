# Fixture rules

- This project is CommonJS. Tests use `require` and Jest, not Vitest or native ESM.
- Tests live under `tests/` and mirror `src/` (`src/greet.js` → `tests/greet.test.js`).
- Match `tests/add.test.js`: single quotes, semicolons, one `describe` per export.
- Do not add dependencies. Do not edit files in `src/`.
