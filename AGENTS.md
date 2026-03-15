# Repository Guidelines

## Project Structure & Module Organization
This repository is currently lightweight and document-first. Existing content lives in `md/` (for example, `md/a_good_tts.md`).

Use the following structure as implementation is added:
- `src/`: application code (e.g., `src/api/`, `src/tts/`, `src/utils/`)
- `tests/`: automated tests, mirroring `src/`
- `assets/`: static resources (sample audio, prompts, fixtures)
- `md/`: design notes, research, and decision records

Keep modules focused: one responsibility per file, and avoid cross-layer imports.

## Build, Test, and Development Commands
Prefer a Python-first workflow unless the project later defines a different stack.
- `python -m venv .venv && source .venv/bin/activate`: create local environment
- `pip install -r requirements.txt`: install runtime dependencies
- `pip install -r requirements-dev.txt`: install dev tooling
- `pytest -q`: run test suite
- `ruff check .`: lint code
- `ruff format .`: format code

If Make targets are added, keep aliases aligned (`make test`, `make lint`, `make format`).

## Coding Style & Naming Conventions
- Use 4-space indentation and UTF-8 encoding.
- Python naming: `snake_case` for functions/files, `PascalCase` for classes, `UPPER_CASE` for constants.
- Keep functions small and typed where practical.
- Public APIs should include concise docstrings and explicit input/output contracts.

## Testing Guidelines
- Framework: `pytest`.
- Place unit tests under `tests/unit/` and integration tests under `tests/integration/`.
- Test files: `test_<module>.py`; test cases: `test_<behavior>()`.
- Add tests for every bug fix and new endpoint/feature.

## Commit & Pull Request Guidelines
No stable Git history exists yet; adopt Conventional Commits:
- `feat: add streaming tts endpoint`
- `fix: handle empty text input`
- `docs: update voice cloning notes`

PRs should include:
- clear summary and scope
- linked issue/task (if available)
- test evidence (`pytest` output or rationale if skipped)
- sample request/response for API changes

## Security & Configuration Tips
- Never commit secrets, API keys, or raw user voice data.
- Store config in `.env` and provide `.env.example`.
- Mask sensitive logs and avoid persisting personally identifiable audio by default.
