# Web App Deployment

## Quick start (Docker Compose)

```bash
cd webapp
cp .env.example .env
# Edit .env — set MCP_SSE_URL and optionally Onshape document IDs

docker compose up --build
```

Open http://localhost:3000

## Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | Nginx + Vite build (chat UI + Three.js viewer) |
| `api` | 8080 | FastAPI backend (sessions, chat SSE, file exports) |
| `redis` | internal | Session/job state |
| `tailscale` (profile) | — | Join tailnet to reach Jarvis MCP |
| `cadquery-worker` (profile) | — | Optional CadQuery sandbox |

## Pipeline modes

The API auto-selects a pipeline based on configuration:

1. **onshape** — Claude CLI + `mcp-proxy` → Jarvis Onshape MCP (native feature trees). Requires:
   - `claude` CLI + mounted `~/.claude` credentials
   - Reachable `MCP_SSE_URL` (Tailscale)
   - `ONSHAPE_DEFAULT_DID/WID/EID` or per-session Onshape targets

2. **cadquery** — Claude generates CadQuery Python, executes locally, exports STL/STEP.

3. **demo** — No Claude/MCP; generates a parametric box from parsed dimensions (or minimal ASCII STL).

Set `PIPELINE_MODE=demo` to force demo mode for UI testing.

## Claude credentials (Mode A)

Mount your local Claude Code credentials:

```yaml
volumes:
  - ~/.claude:/root/.claude:ro
```

Or use the named volume `claude-credentials` and copy credentials in once.

## Tailscale for MCP

If the API container cannot reach `nativedev` directly:

```bash
export TS_AUTHKEY=tskey-auth-...
docker compose --profile tailscale up
```

See `onshape-extension/CLIENT-SETUP.md` for Jarvis MCP server setup.

## Local development (no Docker)

```bash
# Backend
cd webapp/backend
pip install -r requirements.txt
export USE_REDIS=false DATA_DIR=/tmp/3dpp-data SKILLS_DIR=../../skills
uvicorn app.main:app --reload --port 8080

# Frontend
cd webapp/frontend
npm install
npm run dev
```

## API overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service status |
| `/api/materials` | GET | Material list |
| `/api/sessions` | POST | Create design session |
| `/api/sessions/{id}/messages` | POST | Send prompt → `{job_id}` |
| `/api/sessions/{id}/stream?job_id=` | GET (SSE) | Live pipeline events |
| `/api/files/{session}/{name}` | GET | Download STL/STEP |
