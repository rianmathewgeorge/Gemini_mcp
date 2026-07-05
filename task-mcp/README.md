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
