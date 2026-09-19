from simplejustwatchapi import search, providers
from fastmcp import FastMCP

mcp = FastMCP("VOD Search Tool")


@mcp.tool()
def get_streaming_providers(title: str, country: str = "US", language: str = "en") -> str:
    """
    Search for a movie or TV show title and retrieve available streaming providers and direct links.

    Args:
        title: The title of the movie or TV show to search for.
        country: Two-letter country code (defaults to "US").
        language: Two-letter language code (defaults to "en").
    """
    try:
        results = search(title, country=country, language=language, count=1)
        if not results:
            return f"No results found for the title: {title}"

        item = results[0]
        response_lines = [f"Title: {item.title}"]
        response_lines.append("Available streaming providers and offers:")

        if not item.offers:
            return f"Found title '{item.title}', but currently no streaming offers are available."

        for offer in item.offers:
            response_lines.append(f"- **{offer.provider_id}**: {offer.url} (Type: {offer.monetization_type})")

        return "\n".join(response_lines)

    except Exception as e:
        return f"An error occurred while querying JustWatch: {str(e)}"



if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8101)
