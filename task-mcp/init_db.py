import sqlite3, logging, random
from pathlib import Path
from datetime import datetime, timedelta
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")
DB_PATH = Path(__file__).parent / "tasks.db"
SCHEMA = """CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT,
 status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','In Progress','Completed')),
 priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low','Medium','High')),
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);"""
TITLES=["Implement login","Fix payment bug","Design onboarding","Write API docs","Set up CI",
"Refactor auth","Add search","Optimize queries","Build dashboard","Update deps"]
S=["Open","In Progress","Completed"]; P=["Low","Medium","High"]
def init_db():
    c=sqlite3.connect(DB_PATH); c.execute(SCHEMA); c.commit(); c.close()
    logger.info("Table ready.")
def seed_db(n=50):
    c=sqlite3.connect(DB_PATH)
    for i in range(n):
        c.execute("INSERT INTO tasks (title,description,status,priority,created_at) VALUES (?,?,?,?,?)",
          (f"{random.choice(TITLES)} #{i+1}", f"Sample task {i+1}", random.choice(S), random.choice(P),
           (datetime.now()-timedelta(days=random.randint(0,60))).strftime("%Y-%m-%d %H:%M:%S")))
    c.commit(); c.close(); logger.info("Seeded %d tasks", n)
if __name__=="__main__":
    init_db(); seed_db()
