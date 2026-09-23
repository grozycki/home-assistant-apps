from fastmcp import FastMCP
from duckduckgo_search import DDGS
import trafilatura

# Initialize the MCP server
mcp = FastMCP("Web Search")


@mcp.tool()
def search_web(query: str, max_results: int = 4) -> str:
    """
    Searches the web based on the provided query.
    Returns a formatted text list containing the title, URL, and a brief snippet for each result.
    """
    try:
        results = DDGS().text(query, max_results=max_results)
        output = []
        for r in results:
            output.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}")

        return "\n\n".join(output) if output else "No search results found."
    except Exception as e:
        return f"Error during search: {str(e)}"


@mcp.tool()
def read_page(url: str) -> str:
    """
    Downloads and extracts clean text from the specified web page URL.
    Use this tool with URLs obtained from the search_web tool to read the full content.
    It automatically filters out HTML tags, menus, and ads to minimize token usage.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return f"Failed to download resource: {url}"

        # Extract clean content without HTML noise (acts as token compression)
        result = trafilatura.extract(downloaded)
        return result if result else "The page did not contain readable text."
    except Exception as e:
        return f"Error during page analysis: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8405)