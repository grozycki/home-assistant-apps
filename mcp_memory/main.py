import os
import sqlite3
import sys
from datetime import datetime
from fastmcp import FastMCP
import logging

mcp = FastMCP("Local Memory")

DATA_PATH = "/data/memory_db"
os.makedirs(DATA_PATH, exist_ok=True)
DB_FILE = os.path.join(DATA_PATH, "memoryV3.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp_memory")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            fact,
            pipeline_id UNINDEXED,
            timestamp UNINDEXED
        )
    ''')
    conn.commit()
    conn.close()

def print_startup_summary():
    logger.info("=== MCP Memory Startup Summary ===")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT pipeline_id, COUNT(*) FROM memories_fts GROUP BY pipeline_id")
        rows = cursor.fetchall()

        if not rows:
            logger.info("Database is currently empty. No memories stored yet.")
        else:
            total = 0
            for pid, count in rows:
                scope = "GLOBAL" if pid == "global" else pid
                logger.info(f"[{scope}]: {count} memories")
                total += count
            logger.info(f"Total memories in database: {total}")
        conn.close()
    except Exception as e:
        logger.error(f"Could not load summary: {e}")
    logger.info("==================================")

init_db()
print_startup_summary()


@mcp.tool()
def remember_fact(fact: str, pipeline_id: str, is_global: bool = False) -> str:
    """
    Store facts, preferences, or details in the database.

    Args:
        fact: The specific information to remember.
        pipeline_id: CRITICAL - The 26-character alphanumeric string identifying your specific Home Assistant Voice pipeline.
        is_global: Set to True ONLY if the user explicitly wants this applied to the whole house/all devices.
    """
    target_pipeline = "global" if is_global else pipeline_id
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memories_fts (fact, pipeline_id, timestamp) VALUES (?, ?, ?)",
        (fact, target_pipeline, current_time)
    )
    conn.commit()
    conn.close()

    scope = "GLOBALLY" if is_global else f"locally for '{pipeline_id}'"
    logger.info(f"Memorizing fact {scope} at {current_time}")

    return f"Successfully memorized fact {scope} at {current_time}."


@mcp.tool()
def search_memory(query: str, pipeline_id: str, n_results: int = 3) -> str:
    """
    Perform full-text search over stored memories.

    Args:
        query: The search keywords.
        pipeline_id: CRITICAL - The 26-character alphanumeric string identifying your specific Home Assistant Voice pipeline.
        n_results: Maximum number of results to return.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    def do_search(pid: str):
        try:
            cursor.execute(
                "SELECT rowid, fact, pipeline_id, timestamp FROM memories_fts WHERE memories_fts MATCH ? AND pipeline_id = ? LIMIT ?",
                (query, pid, n_results)
            )
            return cursor.fetchall()
        except sqlite3.OperationalError:
            safe_query = f"%{query}%"
            cursor.execute(
                "SELECT rowid, fact, pipeline_id, timestamp FROM memories_fts WHERE fact LIKE ? AND pipeline_id = ? LIMIT ?",
                (safe_query, pid, n_results)
            )
            return cursor.fetchall()

    rows = do_search(pipeline_id)
    if not rows:
        rows = do_search("global")
    conn.close()

    if not rows:
        return f"No matching memories found for '{pipeline_id}' or globally."

    results = [f"ID: {row[0]} | [{'GLOBAL' if row[2] == 'global' else 'LOCAL'}] [{row[3]}] {row[1]}" for row in rows]
    return "\n".join(results)


@mcp.tool()
def list_all_memories(pipeline_id: str) -> str:
    """
    List all stored facts for the specific pipeline AND all global facts.

    Args:
        pipeline_id: CRITICAL - The 26-character alphanumeric string identifying your specific Home Assistant Voice pipeline.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rowid, fact, pipeline_id, timestamp FROM memories_fts WHERE pipeline_id IN (?, 'global')",
        (pipeline_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"Database is empty."

    memories = [
        f"ID: {row[0]} | Scope: {'GLOBAL' if row[2] == 'global' else 'LOCAL'} | Saved: {row[3]} | Fact: {row[1]}" for
        row in rows]
    return "\n".join(memories)


@mcp.tool()
def update_memory(rowid: int, new_fact: str, pipeline_id: str) -> str:
    """
    Update an existing memory's fact text by its ID.

    Args:
        rowid: The numeric ID of the memory to update.
        new_fact: The new text of the fact.
        pipeline_id: CRITICAL - The 26-character alphanumeric string identifying your specific Home Assistant Voice pipeline.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE memories_fts SET fact = ?, timestamp = ? WHERE rowid = ? AND pipeline_id IN (?, 'global')",
        (new_fact, current_time, rowid, pipeline_id)
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return f"Successfully updated memory {rowid} at {current_time}." if updated > 0 else "Failed."


@mcp.tool()
def delete_memory(rowid: int, pipeline_id: str) -> str:
    """
    Delete a previously stored memory by its ID.

    Args:
        rowid: The numeric ID of the memory to delete.
        pipeline_id: CRITICAL - The 26-character alphanumeric string identifying your specific Home Assistant Voice pipeline.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM memories_fts WHERE rowid = ? AND pipeline_id IN (?, 'global')",
        (rowid, pipeline_id)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return f"Successfully deleted memory {rowid}." if deleted > 0 else "Failed."


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)