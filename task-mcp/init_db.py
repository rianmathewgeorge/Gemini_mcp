import sqlite3
import logging
from pathlib import Path
import random
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")

DB_PATH = Path(__file__).parent / "tasks.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'Open'
                CHECK (status IN ('Open', 'In Progress', 'Completed')),
    priority    TEXT NOT NULL DEFAULT 'Medium'
                CHECK (priority IN ('Low', 'Medium', 'High')),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SAMPLE_TITLES = [
    "Implement login page", "Fix payment bug", "Design onboarding flow",
    "Write API documentation", "Set up CI pipeline", "Refactor auth module",
    "Add search feature", "Optimize database queries", "Build analytics dashboard",
    "Migrate to new server", "Update dependencies", "Create user settings page",
    "Add email notifications", "Improve error handling", "Write unit tests",
]
STATUSES = ["Open", "In Progress", "Completed"]
PRIORITIES = ["Low", "Medium", "High"]

def init_db():
    logger.info("Connecting to database at %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(SCHEMA)
        conn.commit()
        logger.info("Table 'tasks' is ready.")
    finally:
        conn.close()
        logger.info("Connection closed.")

def seed_db(count=50):
    logger.info("Seeding %d sample tasks", count)
    conn = sqlite3.connect(DB_PATH)
    try:
        for i in range(count):
            title = f"{random.choice(SAMPLE_TITLES)} #{i + 1}"
            description = f"Auto-generated sample task number {i + 1}"
            status = random.choice(STATUSES)
            priority = random.choice(PRIORITIES)
            created_at = datetime.now() - timedelta(days=random.randint(0, 60))
            conn.execute(
                """INSERT INTO tasks (title, description, status, priority, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (title, description, status, priority, created_at.strftime("%Y-%m-%d %H:%M:%S")),
            )
        conn.commit()
        logger.info("Inserted %d tasks successfully", count)
    finally:
        conn.close()
        logger.info("Connection closed.")

if __name__ == "__main__":
    init_db()
    seed_db()
