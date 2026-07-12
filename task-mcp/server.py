import os, sqlite3, logging, datetime
from pathlib import Path
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

DB_PATH = Path(__file__).parent / "tasks.db"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGO = "HS256"
TOKEN_TTL_MIN = 30
CLIENT_ID = os.getenv("MCP_CLIENT_ID", "mcp-client")
CLIENT_SECRET = os.getenv("MCP_CLIENT_SECRET", "mcp-secret")

ALLOWED_STATUSES = {"Open", "In Progress", "Completed"}
ALLOWED_PRIORITIES = {"Low", "Medium", "High"}

mcp = FastMCP("task-manager", stateless_http=True)
mcp.settings.streamable_http_path = "/"

def get_connection():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn

@mcp.tool()
def get_task(task_id: int) -> dict:
    """Retrieve a single task by its ID."""
    logger.info("get_task task_id=%s", task_id)
    conn = get_connection()
    try:
        row = conn.execute("SELECT id,title,description,status,priority,created_at FROM tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else {"error": f"No task with id {task_id}"}

@mcp.tool()
def search_tasks(status: str | None = None, priority: str | None = None) -> dict:
    """Search tasks, optionally filtering by status and/or priority."""
    logger.info("search_tasks status=%s priority=%s", status, priority)
    if status and status not in ALLOWED_STATUSES:
        return {"error": f"Invalid status '{status}'"}
    if priority and priority not in ALLOWED_PRIORITIES:
        return {"error": f"Invalid priority '{priority}'"}
    cond, params = [], []
    if status: cond.append("status=?"); params.append(status)
    if priority: cond.append("priority=?"); params.append(priority)
    q = "SELECT id,title,description,status,priority,created_at FROM tasks"
    if cond: q += " WHERE " + " AND ".join(cond)
    q += " ORDER BY created_at DESC"
    conn = get_connection()
    try:
        rows = conn.execute(q, params).fetchall()
    finally:
        conn.close()
    tasks = [dict(r) for r in rows]
    return {"count": len(tasks), "tasks": tasks}

@mcp.tool()
def create_task(title: str, description: str | None = None, status: str = "Open", priority: str = "Medium") -> dict:
    """Create a new task and return its generated ID."""
    logger.info("create_task title=%r", title)
    if not title or not title.strip():
        return {"success": False, "error": "Title is required."}
    if status not in ALLOWED_STATUSES:
        return {"success": False, "error": f"Invalid status '{status}'"}
    if priority not in ALLOWED_PRIORITIES:
        return {"success": False, "error": f"Invalid priority '{priority}'"}
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO tasks (title,description,status,priority) VALUES (?,?,?,?)",
                           (title.strip(), description, status, priority))
        conn.commit(); new_id = cur.lastrowid
    finally:
        conn.close()
    return {"success": True, "task_id": new_id}

@mcp.tool()
def task_statistics() -> dict:
    """Return total task count and a breakdown by status."""
    logger.info("task_statistics")
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
        rows = conn.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
    finally:
        conn.close()
    counts = {s: 0 for s in ALLOWED_STATUSES}
    for r in rows: counts[r["status"]] = r["n"]
    return {"total_tasks": total, "open_tasks": counts["Open"],
            "in_progress_tasks": counts["In Progress"], "completed_tasks": counts["Completed"]}

# ---------------- Auth ----------------
def create_token() -> str:
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=TOKEN_TTL_MIN)
    return jwt.encode({"sub": CLIENT_ID, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGO)

def verify_bearer(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

app = FastAPI(title="Task MCP Server", lifespan=lifespan)

@app.post("/token")
def issue_token(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != CLIENT_ID or form.password != CLIENT_SECRET:
        logger.info("Auth FAILED for %s", form.username)
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    logger.info("Token issued to %s", form.username)
    return {"access_token": create_token(), "token_type": "bearer"}

@app.middleware("http")
async def gate_mcp(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        try:
            verify_bearer(request)
        except HTTPException as e:
            logger.info("Blocked unauthenticated MCP request: %s", e.detail)
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)
    return await call_next(request)

app.mount("/mcp", mcp.streamable_http_app())
