import os
import sqlite3
from fastmcp import FastMCP

mcp = FastMCP("Local Memory")

DATA_PATH = "/data/memory_db"
os.makedirs(DATA_PATH, exist_ok=True)
DB_FILE = os.path.join(DATA_PATH, "memoryV2.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            fact,
            pipeline_id UNINDEXED
        )
    ''')
    conn.commit()
    conn.close()

init_db()


@mcp.tool()
def remember_fact(fact: str, pipeline_id: str, is_global: bool = False) -> str:
    """Store facts, preferences, or details. If is_global is True, it will be shared across all assistants."""
    target_pipeline = "global" if is_global else pipeline_id

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memories_fts (fact, pipeline_id) VALUES (?, ?)",
        (fact, target_pipeline)
    )
    conn.commit()
    conn.close()

    scope_name = "GLOBALLY" if is_global else f"locally for pipeline '{pipeline_id}'"
    return f"Successfully memorized fact {scope_name}."


@mcp.tool()
def search_memory(query: str, pipeline_id: str, n_results: int = 3) -> str:
    """Perform full-text search over stored memories. Searches local pipeline memories first, then falls back to global."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    def do_search(pid: str):
        try:
            cursor.execute(
                "SELECT rowid, fact, pipeline_id FROM memories_fts WHERE memories_fts MATCH ? AND pipeline_id = ? LIMIT ?",
                (query, pid, n_results)
            )
            return cursor.fetchall()
        except sqlite3.OperationalError:
            safe_query = f"%{query}%"
            cursor.execute(
                "SELECT rowid, fact, pipeline_id FROM memories_fts WHERE fact LIKE ? AND pipeline_id = ? LIMIT ?",
                (safe_query, pid, n_results)
            )
            return cursor.fetchall()

    rows = do_search(pipeline_id)

    if not rows:
        rows = do_search("global")

    conn.close()

    if not rows:
        return f"No matching memories found for pipeline '{pipeline_id}' or globally."

    results = []
    for row in rows:
        # row[0] = rowid, row[1] = fact, row[2] = pipeline_id
        scope = "GLOBAL" if row[2] == "global" else "LOCAL"
        results.append(f"ID: {row[0]} | [{scope}] {row[1]}")

    return "\n".join(results)


@mcp.tool()
def list_all_memories(pipeline_id: str) -> str:
    """List all stored facts for the specific pipeline AND all global facts."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rowid, fact, pipeline_id FROM memories_fts WHERE pipeline_id IN (?, 'global')",
        (pipeline_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"The memory database for pipeline '{pipeline_id}' (including global) is currently empty."

    memories = []
    for row in rows:
        scope = "GLOBAL" if row[2] == "global" else "LOCAL"
        memories.append(f"ID: {row[0]} | Scope: {scope} | Fact: {row[1]}")
    return "\n".join(memories)


@mcp.tool()
def update_memory(rowid: int, new_fact: str, pipeline_id: str) -> str:
    """Update an existing memory's fact text by its ID. Cannot change the scope (local/global)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE memories_fts SET fact = ? WHERE rowid = ? AND pipeline_id IN (?, 'global')",
        (new_fact, rowid, pipeline_id)
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    if updated > 0:
        return f"Successfully updated memory with ID {rowid}."
    return f"Failed. No memory found with ID {rowid} for this pipeline or globally."


@mcp.tool()
def delete_memory(rowid: int, pipeline_id: str) -> str:
    """Delete a previously stored memory by its ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM memories_fts WHERE rowid = ? AND pipeline_id IN (?, 'global')",
        (rowid, pipeline_id)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted > 0:
        return f"Successfully deleted memory with ID {rowid}."
    return f"Failed. No memory found with ID {rowid} for this pipeline or globally."


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
