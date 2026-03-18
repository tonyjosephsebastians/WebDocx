# WebDocx

WebDocx is a DOCX-first collaborative document workspace built on top of ONLYOFFICE Docs. It provides a React application shell, a FastAPI backend, version history, sharing, comparison-draft workflows, and ONLYOFFICE callback orchestration for web-based editing and review.

This repository contains the application code. It does **not** vendor the ONLYOFFICE Document Server source or binaries. Document Server should be installed and run separately, then connected through environment variables.

## What It Does

- Create blank DOCX files or upload existing `.docx` documents
- Open documents in a browser through ONLYOFFICE Docs
- Share documents with role-based access: `owner`, `editor`, `reviewer`, `commenter`, `viewer`
- Generate non-destructive comparison drafts from two workspace documents
- Persist save checkpoints and final saves from ONLYOFFICE callbacks
- Browse version history and restore prior versions
- Keep a Word-like outer workspace UI around the native ONLYOFFICE editor

## Stack

- Frontend: Vite, React, TypeScript, TanStack Query, TanStack Router, Tailwind CSS, Radix UI
- Backend: FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings
- Storage: local filesystem in v1, with a storage service abstraction for later S3/MinIO support
- Database: SQLite for simple local development, PostgreSQL for a more production-like setup
- Editor engine: ONLYOFFICE Docs API

## Repository Layout

```text
.
├── backend/        FastAPI API, ORM models, services, tests, migrations
├── frontend/       React application shell and ONLYOFFICE embedding layer
├── infra/          Reverse-proxy starter config
├── compose.yaml    Local PostgreSQL helper
└── README.md
```

## High-Level Architecture

```mermaid
flowchart LR
    U["Browser User"] --> F["React Frontend"]
    F --> B["FastAPI Backend"]
    B --> DB["SQLite / PostgreSQL"]
    B --> FS["Local File Storage"]
    F --> OO["ONLYOFFICE Docs"]
    OO --> B
    OO --> FS
```

### Editing Request Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant OnlyOffice
    participant Storage

    User->>Frontend: Open document
    Frontend->>Backend: POST /api/documents/{id}/editor-config
    Backend-->>Frontend: signed editor config
    Frontend->>OnlyOffice: initialize Docs API editor
    OnlyOffice->>Backend: GET document binary URL
    Backend->>Storage: read current DOCX
    Backend-->>OnlyOffice: file response
    User->>OnlyOffice: edit document
    OnlyOffice->>Backend: POST /api/onlyoffice/callback
    Backend->>Storage: persist new binary and changes archive
    Backend->>DB: create DocumentVersion
    Backend-->>OnlyOffice: { error: 0 }
```

### Comparison Workflow

```mermaid
flowchart TD
    A["Source document"] --> C["POST /api/documents/{id}/compare"]
    B["Revised document"] --> C
    C --> D["Duplicate source into new comparison document"]
    D --> E["Store ComparisonDocument link"]
    E --> F["Open comparison draft in editor"]
    F --> G["Inject revised document into ONLYOFFICE compare flow"]
```

## Backend Design

The backend is responsible for:

- authentication and workspace membership
- document metadata and file-version persistence
- editor session tracking
- signed ONLYOFFICE editor config generation
- callback handling for save and checkpoint events
- force-save command submission to ONLYOFFICE
- compare-draft orchestration

### Core Models

- `User`
- `Workspace`
- `Membership`
- `Document`
- `DocumentBinary`
- `DocumentVersion`
- `EditorSession`
- `ShareGrant`
- `ComparisonDocument`
- `ActivityEvent`

### Important Backend Files

- [backend/app/main.py](backend/app/main.py)
- [backend/app/routers/auth.py](backend/app/routers/auth.py)
- [backend/app/routers/documents.py](backend/app/routers/documents.py)
- [backend/app/routers/onlyoffice.py](backend/app/routers/onlyoffice.py)
- [backend/app/services/documents.py](backend/app/services/documents.py)
- [backend/app/services/onlyoffice.py](backend/app/services/onlyoffice.py)

## Frontend Design

The frontend is intentionally not a reimplementation of Microsoft Word. It provides the product shell around ONLYOFFICE:

- login and account creation
- workspace document library
- upload/create actions
- sharing and compare dialogs
- editor header actions
- version and activity side panel

### Important Frontend Files

- [frontend/src/pages/workspace-page.tsx](frontend/src/pages/workspace-page.tsx)
- [frontend/src/pages/editor-page.tsx](frontend/src/pages/editor-page.tsx)
- [frontend/src/components/onlyoffice-editor.tsx](frontend/src/components/onlyoffice-editor.tsx)
- [frontend/src/lib/api.ts](frontend/src/lib/api.ts)
- [frontend/src/lib/session.tsx](frontend/src/lib/session.tsx)

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.12+
- pip
- OPTIONAL: Docker Desktop for PostgreSQL
- REQUIRED for actual document editing: a running ONLYOFFICE Docs instance

## 1. Configure the Backend

```powershell
cd backend
Copy-Item .env.example .env
```

Recommended simple local `.env`:

```env
APP_NAME=Word Workspace API
APP_ENV=development
APP_SECRET_KEY=replace-with-a-long-random-string
APP_ACCESS_TOKEN_EXPIRE_MINUTES=10080
APP_PUBLIC_URL=http://127.0.0.1:8000
APP_DATABASE_URL=sqlite:///./word_workspace.db
APP_STORAGE_ROOT=storage
APP_CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
APP_ONLYOFFICE_DOCUMENT_SERVER_URL=http://localhost:8080
APP_ONLYOFFICE_BROWSER_SECRET=replace-with-the-same-long-secret
APP_ONLYOFFICE_INBOX_SECRET=replace-with-the-same-long-secret
APP_ONLYOFFICE_OUTBOX_SECRET=replace-with-the-same-long-secret
```

Install and run:

```powershell
pip install -e .[dev]
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## 2. Configure the Frontend

```powershell
cd frontend
Copy-Item .env.example .env
```

Frontend `.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Install and run:

```powershell
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

## 3. OPTIONAL: Run PostgreSQL

From the repo root:

```powershell
docker compose up -d postgres
```

Then change backend `.env`:

```env
APP_DATABASE_URL=postgresql+psycopg://word:word@localhost:5432/word_workspace
```

## 4. REQUIRED: Install and Run ONLYOFFICE Docs

This application needs a real ONLYOFFICE Document Server to render the embedded editor.

Recommended local path on a personal Windows machine:

- run ONLYOFFICE in Docker on a Linux-compatible environment
- expose it at `http://localhost:8080`

Example:

```powershell
docker run -d `
  --name onlyoffice-documentserver `
  -p 8080:80 `
  --restart=always `
  -e JWT_SECRET=replace-with-the-same-long-secret `
  onlyoffice/documentserver
```

Then verify:

- `http://localhost:8080/example`
- `http://localhost:8080/web-apps/apps/api/documents/api.js`

If your ONLYOFFICE host is not `localhost:8080`, update `APP_ONLYOFFICE_DOCUMENT_SERVER_URL`.

## How to Run Everything Together

Open three terminals.

### Terminal 1

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### Terminal 3

Run ONLYOFFICE Docs or PostgreSQL if needed.

## API Surface

### Auth

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Documents

- `GET /api/documents`
- `POST /api/documents`
- `GET /api/documents/{id}`
- `PATCH /api/documents/{id}`
- `POST /api/documents/{id}/duplicate`
- `POST /api/documents/{id}/share`
- `POST /api/documents/{id}/editor-config?mode=view|comment|review|edit`
- `GET /api/documents/{id}/history`
- `GET /api/documents/{id}/history/editor`
- `GET /api/documents/{id}/history/{version}/editor`
- `POST /api/documents/{id}/history/{version}/restore`
- `POST /api/documents/{id}/compare`
- `GET /api/documents/{id}/download`

### ONLYOFFICE Integration

- `POST /api/onlyoffice/callback`
- `POST /api/onlyoffice/forcesave?document_id=...`

## Current Operational Notes

- v1 supports `.docx` uploads only
- mobile editing is out of scope
- the outer application shell is customized, but the embedded editor UI remains native ONLYOFFICE
- comparison is non-destructive: the source document is duplicated into a comparison draft
- local filesystem storage is used by default

## Verification

### Backend tests

```powershell
cd backend
pytest -q
```

### Frontend lint

```powershell
cd frontend
npm run lint
```

### Frontend production build

```powershell
cd frontend
npm run build
```

## Known Gaps

- There is no live end-to-end browser automation against a real ONLYOFFICE server in this repo yet.
- Local development defaults to SQLite for convenience; production should use PostgreSQL and a durable file store.
- The reverse-proxy file in `infra/Caddyfile` is a starter config, not a production-hardened deployment.

## Publishing Notes

This repo intentionally excludes the downloaded `DocumentServer/` source tree because:

- it is large and unnecessary for application development
- it is a separate upstream project
- the app only needs a reachable running ONLYOFFICE instance

## License and Upstream

This app integrates with ONLYOFFICE Docs Community Edition. Review ONLYOFFICE licensing before using this application for a commercial SaaS product.
