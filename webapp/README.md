# 3D Print Pipeline — Web App

AI-powered web interface for the 3D print pipeline: chat with the design agent, watch the pipeline run, preview STL exports in Three.js, and iterate on designs.

## Features

- **Chat UI** — Send natural-language prompts; stream agent phases, tool calls, and responses via SSE
- **3D viewer** — Three.js STL preview with orbit controls
- **Pipeline modes** — Onshape MCP (primary), CadQuery fallback, demo mode for offline testing
- **Material selector** — 15 materials from `skills/print-profiles/materials.json`
- **Session continuity** — Claude `--resume` for iterative edits (Onshape path)
- **Docker Compose** — Redis, API, frontend, optional Tailscale + CadQuery worker

## Quick start

### Docker (recommended)

```bash
cd webapp
cp .env.example .env
docker compose up --build
```

Open http://localhost:3000

### Local development

```bash
# Terminal 1 — API
cd webapp/backend
pip install -r requirements.txt
export USE_REDIS=false DATA_DIR=/tmp/3dpp-data SKILLS_DIR=../../skills
uvicorn app.main:app --reload --port 8080

# Terminal 2 — Frontend
cd webapp/frontend
npm install
npm run dev
```

Open http://localhost:3000

## Configuration

See [docs/DEPLOY.md](docs/DEPLOY.md) for full deployment guide.

| Variable | Purpose |
|----------|---------|
| `MCP_SSE_URL` | Jarvis Onshape MCP SSE endpoint |
| `CLAUDE_MODE` | `auto`, `cli`, `api`, or `demo` |
| `PIPELINE_MODE` | `auto`, `onshape`, `cadquery`, or `demo` |
| `ONSHAPE_DEFAULT_DID/WID/EID` | Default Onshape document |

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Service status |
| `GET /api/materials` | Material list |
| `POST /api/sessions` | Create session |
| `POST /api/sessions/{id}/messages` | Send prompt |
| `GET /api/sessions/{id}/stream?job_id=` | SSE event stream |
| `GET /api/files/{session}/{name}` | Download STL/STEP |

## Suggested next features

- Image upload → `image-to-3d` skill integration
- Variable Studio parameter panel (live dimension edits)
- Job history sidebar per session
- Onshape deep-link + live feature tree poll
- WebSocket for bidirectional cancel/typing indicators
