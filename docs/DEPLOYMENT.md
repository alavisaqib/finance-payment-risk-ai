# Running on a server

## Local validation

Install Python 3.13 requirements in a virtual environment, run `python -m pytest -q`, then start Uvicorn as described in the README. `python -m scripts.evaluate` regenerates the evaluation report and example response. Default demo mode never calls a paid provider. The model and evidence corpus load into memory on first request.

## Docker Compose on a Linux host

1. Install Docker Engine and the Compose plugin through the operating system's supported instructions.
2. Clone this repository. Copy `.env.example` to `.env`; set a strong `APP_API_KEY` before allowing shared access.
3. Run `docker compose up --build -d` and `docker compose ps`.
4. Check `curl http://127.0.0.1:8000/health` and make an authenticated request to `/api/decisions` using `examples/request.json`.
5. Inspect `docker compose logs --tail=100 api`. The application runs as UID 10001 and writes state only to its named volume.

The default port mapping is loopback-only. Remote use needs an authenticated TLS reverse proxy or private network, request size/rate controls, managed secrets, backups and a retention policy. A single static API key is a demonstration access control, not a user/tenant identity system. `/health`, static files and the OpenAPI schema remain public; they contain no run history or credentials. Protect all routes at your reverse proxy when appropriate.

SQLite is appropriate for one instance. Do not share its file over network storage or scale replicas over the same volume. A production deployment should move persistent data to a managed database and establish access and audit controls. The current service stores numerical scenario inputs and generated advice; never submit protected or confidential data to this demonstration.

## Environment

- `LLM_PROVIDER`: `demo` or `openai`; defaults to `demo`.
- `OPENAI_API_KEY`: required only for live mode.
- `OPENAI_MODEL`: an account-accessible model supporting Responses structured output.
- `APP_API_KEY`: optional locally; required by the deployment procedure before shared access.
- `STATE_DIR`: writable SQLite location; defaults to the repository's ignored `state/` directory.
- `PORT`: Compose host port; defaults to 8000.

Compose reads `.env`. Local Uvicorn loads it only when launched with `--env-file .env`. MCP hosts pass environment variables explicitly. On Windows, change the example MCP executable to the absolute `.venv\\Scripts\\python.exe` path and use the absolute repository path as `cwd`.

## Updating and rollback

Keep the prior image available, back up the stopped instance's named volume, run tests, build a new image and restart one instance. Inspect health and a real demo request before switching traffic. No database migrations currently exist beyond idempotent table creation. Replacing policy documents, model code or data requires restart. For rollback, restore the prior image and compatible state; do not delete the volume to restart an application.

## Verification boundaries

The GitHub Actions workflow runs tests, checks deterministic data regeneration, builds the Linux Docker image and smoke-tests an API decision. Consult the actual Actions result rather than assuming a green build. A local Python test run does not verify Docker or a paid provider. Live OpenAI tests use a mocked structured-output contract by default; an optional manual live request requires your own key and budget.
