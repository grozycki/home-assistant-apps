import os
import json
import sqlite3
from mcp.server.mcpserver import MCPServer

DEFAULT_CATEGORY = "general"
options_path = "/data/options.json"
if os.path.exists(options_path):
    try:
        with open(options_path, "r") as f:
            options = json.load(f)
            DEFAULT_CATEGORY = options.get("default_category", "general")
    except Exception:
        pass

mcp = MCPServer("Local MCP Memory")

DATA_PATH = "/data/memory_db"
os.makedirs(DATA_PATH, exist_ok=True)
DB_FILE = os.path.join(DATA_PATH, "memory.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            fact,
            category
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@mcp.tool()
def remember_fact(fact: str, category: str = DEFAULT_CATEGORY) -> str:
    """Store important facts, preferences, or details into the local text memory database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memories_fts (fact, category) VALUES (?, ?)", (fact, category))
    conn.commit()
    conn.close()
    return f"Successfully memorized fact under category '{category}'."

@mcp.tool()
def search_memory(query: str, n_results: int = 3) -> str:
    """Perform full-text search over stored local memories to retrieve relevant context."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fact, category FROM memories_fts WHERE memories_fts MATCH ? LIMIT ?", (query, n_results))
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        cursor.execute("SELECT fact, category FROM memories_fts LIMIT ?", (n_results,))
        rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No matching memories found in the local database."

    results = [f"[{row[1]}] {row[0]}" for row in rows]
    return str(results)

@mcp.tool()
def list_all_memories() -> str:
    """List all stored facts and memories from the local database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, fact, category FROM memories_fts")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "The memory database is currently empty."

    memories = [f"ID: {row[0]} | Category: {row[2]} | Fact: {row[1]}" for row in rows]
    return "\n".join(memories)

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
