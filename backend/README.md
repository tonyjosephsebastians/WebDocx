# Word Workspace Backend

FastAPI backend for the DOCX workspace app.

## Quick start

1. Create a virtual environment.
2. Install dependencies:

```powershell
pip install -e .[dev]
```

3. Copy `.env.example` to `.env` and update the values.
4. Run the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

5. Run tests:

```powershell
pytest
```
