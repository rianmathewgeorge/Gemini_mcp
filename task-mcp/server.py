import sqlite3
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

DB_PATH = Path(__file__).parent / "tasks.db"

ALLOWED_STATUSES = {"Open", "In Progress", "Completed"}
ALLOWED_PRIORITIES = {"Low", "Medium", "High"}

mcp = FastMCP("task-manager")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def get_task(task_id: int) -> dict:
    """Retrieve a single task by its ID.

    Args:
        task_id: The unique integer ID of the task to fetch.
    """
    logger.info("get_task called with task_id=%s", task_id)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, title, description, status, priority, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        logger.info("get_task: no task found with id=%s", task_id)
        return {"error": f"No task found with id {task_id}"}

    logger.info("get_task: found task id=%s", task_id)
    return dict(row)


@mcp.tool()
def search_tasks(status: str | None = None, priority: str | None = None) -> dict:
    """Search for tasks, optionally filtering by status and/or priority.

    Args:
        status: Optional status filter. One of 'Open', 'In Progress', 'Completed'.
        priority: Optional priority filter. One of 'Low', 'Medium', 'High'.
    """
    logger.info("search_tasks called with status=%s priority=%s", status, priority)

    # 1. Validate inputs before touching the database
    if status is not None and status not in ALLOWED_STATUSES:
        logger.info("search_tasks: rejected invalid status=%s", status)
        return {"error": f"Invalid status '{status}'. Must be one of {sorted(ALLOWED_STATUSES)}"}
    if priority is not None and priority not in ALLOWED_PRIORITIES:
        logger.info("search_tasks: rejected invalid priority=%s", priority)
        return {"error": f"Invalid priority '{priority}'. Must be one of {sorted(ALLOWED_PRIORITIES)}"}

    # 2. Build the WHERE clause dynamically, but safely
    conditions = []
    params = []
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if priority is not None:
        conditions.append("priority = ?")
        params.append(priority)

    query = "SELECT id, title, description, status, priority, created_at FROM tasks"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    # 3. Run it and convert every row to a dict
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    tasks = [dict(row) for row in rows]
    logger.info("search_tasks: found %d tasks", len(tasks))
    return {"count": len(tasks), "tasks": tasks}


@mcp.tool()
def create_task(title: str, description: str | None = None,
                status: str = "Open", priority: str = "Medium") -> dict:
    """Create a new task and return its generated ID.

    Args:
        title: The task title (required, cannot be empty).
        description: Optional longer description of the task.
        status: Task status. One of 'Open', 'In Progress', 'Completed'. Defaults to 'Open'.
        priority: Task priority. One of 'Low', 'Medium', 'High'. Defaults to 'Medium'.
    """
    logger.info("create_task called with title=%r status=%s priority=%s", title, status, priority)

    # Validate every input before writing
    if not title or not title.strip():
        logger.info("create_task: rejected empty title")
        return {"success": False, "error": "Title is required and cannot be empty."}
    if status not in ALLOWED_STATUSES:
        logger.info("create_task: rejected invalid status=%s", status)
        return {"success": False, "error": f"Invalid status '{status}'. Must be one of {sorted(ALLOWED_STATUSES)}"}
    if priority not in ALLOWED_PRIORITIES:
        logger.info("create_task: rejected invalid priority=%s", priority)
        return {"success": False, "error": f"Invalid priority '{priority}'. Must be one of {sorted(ALLOWED_PRIORITIES)}"}

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO tasks (title, description, status, priority) VALUES (?, ?, ?, ?)",
            (title.strip(), description, status, priority),
        )
        conn.commit()
        new_id = cursor.lastrowid
    finally:
        conn.close()

    logger.info("create_task: created task id=%s", new_id)
    return {"success": True, "task_id": new_id}


@mcp.tool()
def task_statistics() -> dict:
    """Return summary statistics about all tasks: the total count and a
    breakdown of how many tasks are in each status."""
    logger.info("task_statistics called")
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"
        ).fetchall()
    finally:
        conn.close()

    # Start every allowed status at 0 so a status with no tasks still appears.
    counts = {status: 0 for status in ALLOWED_STATUSES}
    for row in rows:
        counts[row["status"]] = row["n"]

    result = {
        "total_tasks": total,
        "open_tasks": counts["Open"],
        "in_progress_tasks": counts["In Progress"],
        "completed_tasks": counts["Completed"],
    }
    logger.info("task_statistics: %s", result)
    return result


if __name__ == "__main__":
    mcp.run()
