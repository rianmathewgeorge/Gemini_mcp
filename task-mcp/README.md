# Task Manager MCP Server

An MCP (Model Context Protocol) server that lets an AI assistant query and manage a
local SQLite database of project tasks, paired with a Google Gemini client that turns
plain English into tool calls.

## Overview

The project has three parts that work together:

- **`init_db.py`** builds the SQLite database and fills it with 50 sample tasks.
- **`server.py`** is the MCP server. It exposes four tools an AI can call: fetch a
  single task, search tasks, create a task, and get statistics.
- **`client.py`** connects Gemini to the server. You ask a question in natural
  language, Gemini reads the available tools, picks the right one, calls it through
  the server, and replies with a natural answer.

The flow is: **you → Gemini (decides) → MCP client → MCP server → SQLite → back up as JSON.**

## Requirements

- Python 3.10 or newer
- A Google Gemini API key ([aistudio.google.com](https://aistudio.google.com/apikey))

## Project structure

| File | Purpose |
| --- | --- |
| `init_db.py` | Creates the database schema and seeds 50 sample tasks |
| `server.py` | MCP server exposing the four task tools |
| `client.py` | Gemini client that calls the tools from natural language |
| `requirements.txt` | Python dependencies |
| `.env` | Holds your Gemini API key (create locally, never commit) |
| `tasks.db` | The generated SQLite database (never commit) |

## Setup

**1. Create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Add your Gemini API key**

Create a file named `.env` in the project folder with a single line:

```
GEMINI_API_KEY=your_key_here
```

The key is loaded from this file at runtime and never appears in the source code.
The `.gitignore` keeps `.env` out of version control.

**4. Initialise the database**

```bash
python init_db.py
```

This creates `tasks.db` and populates it with 50 sample tasks. Running it again adds
another 50; to reset to a clean 50, delete `tasks.db` and run the command once more.

## Running

### Inspect the server (optional)

The MCP Inspector is a browser tool for testing the server directly. It lists the
tools and lets you call each one by hand.

```bash
mcp dev server.py
```

Open the local URL it prints, connect, and try the tools.

### Run the Gemini client

```bash
python client.py
```

Then ask questions in plain English:

```
You: how many tasks are open?
You: show me the high priority tasks
You: create a task called "Review pull request" with high priority
You: what are the overall task statistics?
```

Type `quit` to exit.

## Database schema

Table `tasks`:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER | Primary key, auto-assigned |
| `title` | TEXT | Required |
| `description` | TEXT | Optional |
| `status` | TEXT | One of `Open`, `In Progress`, `Completed` (default `Open`) |
| `priority` | TEXT | One of `Low`, `Medium`, `High` (default `Medium`) |
| `created_at` | DATETIME | Set automatically on creation |

Allowed values for `status` and `priority` are enforced both in the tool code and by
`CHECK` constraints in the database.

## Tools

### get_task
Retrieve a single task by ID.

Input:
```json
{ "task_id": 1 }
```
Output:
```json
{ "id": 1, "title": "Implement login page", "description": "...",
  "status": "In Progress", "priority": "High", "created_at": "2026-06-01 10:00:00" }
```

### search_tasks
Return tasks, optionally filtered by status and/or priority. With no filters it
returns all tasks.

Input:
```json
{ "status": "Open" }
```
Output:
```json
{ "count": 12, "tasks": [ ... ] }
```

### create_task
Create a new task. Only `title` is required; `status` defaults to `Open` and
`priority` to `Medium`.

Input:
```json
{ "title": "Build Dashboard", "description": "Create analytics dashboard", "priority": "Medium" }
```
Output:
```json
{ "success": true, "task_id": 51 }
```

### task_statistics
Return a summary count of all tasks by status.

Input:
```json
{}
```
Output:
```json
{ "total_tasks": 50, "open_tasks": 20, "in_progress_tasks": 12, "completed_tasks": 18 }
```

## Design notes

- **Parameterized queries only.** Every value passed to SQL goes through a `?`
  placeholder, never string formatting. This makes SQL injection structurally
  impossible.
- **Input validation.** Each tool validates its inputs before touching the database
  and returns a clear error for invalid values rather than failing silently.
- **Structured JSON responses.** Every tool returns a predictable JSON shape, so the
  AI receives clearly labelled fields.
- **Logging on every operation.** Each database action is logged with a timestamp and
  severity level. Logs go to stderr so they never interfere with the MCP protocol,
  which uses stdout.
