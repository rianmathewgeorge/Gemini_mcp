# Task MCP — Authenticated Client/Server (FastAPI)

Two separate FastAPI services. The **server** exposes the MCP task tools over HTTP,
protected by JWT auth. The **client** must authenticate before it can complete the
MCP handshake or call any tool, and it uses Gemini to drive the tools from natural language.

## Architecture

```
User -> client (FastAPI /chat) --[1: POST /token, get JWT]--> server (FastAPI)
                                --[2: MCP handshake + tool calls with Bearer JWT]--> server /mcp -> SQLite
```

The server rejects any `/mcp` request (including the handshake) that lacks a valid JWT.

## Files
- `server.py`  — FastAPI app: `/token` (issues JWT) + `/mcp` (MCP tools, auth-gated)
- `client.py`  — FastAPI app: `/chat` (authenticates, handshakes, runs Gemini + tools)
- `init_db.py` — creates and seeds the SQLite database (50 tasks)

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in GEMINI_API_KEY and change the secrets
python init_db.py
```

## Run (two terminals, both with .venv active)
```bash
# terminal 1 — server on :8000
uvicorn server:app --port 8000

# terminal 2 — client on :8001
uvicorn client:app --port 8001
```

Then ask it something:
```bash
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" \
  -d '{"message": "how many tasks are open?"}'
```

## Auth model
- Client authenticates to `POST /token` with `MCP_CLIENT_ID` / `MCP_CLIENT_SECRET`.
- Server returns a short-lived JWT (HS256, 30 min) signed with `JWT_SECRET`.
- Client sends `Authorization: Bearer <jwt>` on every MCP request.
- A server middleware validates the JWT before allowing anything under `/mcp`.

## Notes
- Tools use parameterized queries, input validation, structured JSON, and logging.
- `.env`, `tasks.db`, and logs are gitignored.
