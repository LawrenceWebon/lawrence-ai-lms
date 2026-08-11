# API process

Run the FastAPI foundation entrypoint with:

```text
PYTHONPATH=backend/src uv run --project backend uvicorn lms.api.main:app
```

Step 0 exposes only `/health`; F-001 business routes remain absent.
