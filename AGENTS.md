# Repository Guidelines

## Project Structure & Module Organization
- `app/main.py` boots the FastAPI app and exposes root/health probes.
- `app/api` holds versioned routers; `app/api/v1/endpoints` contains feature routes (keywords, trends, promo, upload, crawler, etc.). Register new routes in `app/api/v1/router.py`.
- `app/services` contains business logic (LLM, relevance, promo generation, uploaders, scraping, publishing). Keep HTTP and external calls here, not in handlers.
- `app/schemas` defines Pydantic request/response models; `app/prompts` stores prompt templates; `app/flows/write_graph.py` is the LangGraph-based orchestration for automated writing.
- `app/config.py` centralizes environment access; load secrets via `.env`. `tests/` holds pytest suites. `tmp/` is scratch data/screenshots and is not treated as source.

## Build, Test, and Development Commands
- Install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run API locally: `uvicorn app.main:app --reload`
- Docker workflow: `docker-compose up web` for live reload; `docker-compose run --rm test` for an isolated test run (includes Playwright/Chromium deps).
- Tests: `python -m pytest` (respects `pytest.ini` with `tests/` as root). Set `PYTHONPATH=/app` if running outside the repo root.

## Coding Style & Naming Conventions
- Python 3.11, FastAPI. Follow PEP8 with 4-space indents; snake_case for functions/vars, UpperCamelCase for classes, ALL_CAPS for constants.
- Keep type hints and module docstrings (`from __future__ import annotations` is standard here). Prefer Pydantic models for request/response shapes.
- Endpoints stay `async` and thin; delegate to `app.services.*`. Reuse shared HTTP clients where possible and avoid direct `os.getenv`—use `app.config` getters.
- Add new versioned endpoints under `/api` and keep names lowercased; keep prompt files small and text-only.

## Testing Guidelines
- Tests live in `tests/` and follow `test_*.py` naming. Use `fastapi.testclient.TestClient` or async `httpx.AsyncClient` as in existing suites.
- Override dependencies via `app.dependency_overrides[...]` in tests and clear them afterward (`tests/test_llm.py` shows the pattern).
- Cover new service logic and API paths, including error paths and env fallbacks; prefer fixtures/mocks over network calls. Keep assertions on status codes and payload schemas.

## Commit & Pull Request Guidelines
- Recent history favors short, imperative messages (`added uploader controller`, `removed loggers on naver_blog.py`); keep titles under ~60 chars and present tense.
- PRs should summarize scope, list new env vars (LOG_* endpoints, `OPENAI_API_KEY`, X tokens), and mention any Playwright/Chromium expectations.
- Include test evidence (`python -m pytest` or `docker-compose run --rm test`) and attach screenshots/log snippets for crawler or upload flows when behavior changes.

## Security & Config Notes
- Store secrets in `.env`; `app/config.py` documents required keys. Never commit `.env` or `tmp/` artifacts.
- Docker image installs Playwright/Chromium; if running locally without Docker, run `playwright install chromium` once.
