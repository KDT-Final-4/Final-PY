from fastapi import FastAPI

app = FastAPI(title="Final PY API", version="0.1.0")


@app.get("/", summary="Root endpoint")
async def read_root() -> dict[str, str]:
    """Simple root endpoint to verify the API is running."""
    return {"message": "Hello, FastAPI"}


@app.get("/health", summary="Health check")
async def health_check() -> dict[str, str]:
    """Liveness probe for container orchestration."""
    return {"status": "ok"}
