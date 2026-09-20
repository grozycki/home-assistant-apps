from simplejustwatchapi import search, seasons, episodes, popular
from fastmcp import FastMCP
import os

DEFAULT_COUNTRY = os.getenv("COUNTRY", "UK")
DEFAULT_LANG = os.getenv("LANGUAGE", "en")

mcp = FastMCP("VOD Search Tool")


@mcp.tool()
def get_streaming_providers(title: str, country: str = DEFAULT_COUNTRY, language: str = DEFAULT_LANG) -> str:
    """
    Search for a movie or TV show title and retrieve available streaming providers and direct links.
    Use this tool exclusively when a user asks about streaming availability, VOD platforms, or where to watch a specific title.

    Args:
        title: The exact title of the movie or TV show to search for.
        country: Two-letter country code for regional availability (defaults to UK, change to PL for Poland if requested).
        language: Two-letter language code for results (defaults to en).
    """
    try:
        results = search(title, country=country, language=language, count=1)
        if not results:
            return f"No results found for the title: {title}"

        item = results[0]
        response_lines = [f"Title: {item.title} ({item.release_year or 'N/A'})"]
        response_lines.append(f"JustWatch URL: {item.url}")
        response_lines.append("Available streaming providers and offers:")

        if not item.offers:
            return f"Found title '{item.title}', but currently no streaming offers are available."

        for offer in item.offers:
            provider_name = offer.package.name if offer.package else "Unknown Provider"
            monetization = offer.monetization_type
            presentation = offer.presentation_type
            price = f" - {offer.price_string}" if offer.price_string else ""

            response_lines.append(
                f"- **{provider_name}** [{monetization} / {presentation}{price}]: {offer.url}"
            )

        return "\n".join(response_lines)
    except Exception as e:
        return f"An error occurred while querying JustWatch: {str(e)}"


@mcp.tool()
def get_show_episodes(title: str, country: str = DEFAULT_COUNTRY, language: str = DEFAULT_LANG) -> str:
    """
    Search for a TV show and retrieve its list of seasons and episodes.
    Use this tool when the user asks about specific episodes, season numbers, or the latest episode of a series.

    Args:
        title: The title of the TV show.
        country: Two-letter country code (defaults to UK).
        language: Two-letter language code (defaults to en).
    """
    try:
        results = search(title, country=country, language=language, count=1)
        if not results:
            return f"No TV show found for the title: {title}"

        show = results[0]
        show_id = getattr(show, 'entry_id', None) or str(show.object_id)

        response_lines = [f"Show: {show.title} ({show.release_year or 'N/A'})"]

        show_seasons = seasons(show_id, country=country, language=language)
        if not show_seasons:
            return f"Found show '{show.title}', but no seasons data is available."

        response_lines.append("Seasons and Episodes:")

        for season in show_seasons:
            season_num = getattr(season, 'season_number', 'N/A')
            season_title = getattr(season, 'title', f"Season {season_num}")
            season_id = getattr(season, 'entry_id', None) or str(season.object_id)

            response_lines.append(f"\n### {season_title} (Season {season_num})")

            try:
                show_episodes = episodes(season_id, country=country, language=language)
                if show_episodes:
                    for ep in show_episodes:
                        ep_num = getattr(ep, 'episode_number', '?')
                        ep_title = getattr(ep, 'title', 'Untitled')
                        response_lines.append(f"  - Ep. {ep_num}: {ep_title}")
                else:
                    response_lines.append("  - No episode list available for this season.")
            except Exception:
                response_lines.append("  - Error fetching episodes for this season.")

        return "\n".join(response_lines)
    except Exception as e:
        return f"An error occurred while fetching episodes: {str(e)}"

@mcp.tool()
def get_popular_releases(provider_codes: str = "", count: int = 10, country: str = DEFAULT_COUNTRY,
                         language: str = DEFAULT_LANG) -> str:
    """
    Retrieve popular or trending movies and TV shows, optionally filtered by streaming providers.
    Use this tool when the user asks about new releases, popular titles, or what's trending on platforms like Netflix, HBO Max, Disney+, etc.

    Args:
        provider_codes: Comma-separated JustWatch provider technical shortcuts if known (e.g., 'nfx' for Netflix, 'mxx' for Max, 'amz' for Amazon). Leave empty for general popular titles.
        count: Number of results to return (defaults to 10).
        country: Two-letter country code (defaults to UK).
        language: Two-letter language code (defaults to en).
    """
    try:
        providers_list = [p.strip() for p in provider_codes.split(",")] if provider_codes else None
        results = popular(country=country, language=language, count=count, providers=providers_list)

        if not results:
            return "No popular releases found."

        response_lines = [f"Popular / Trending titles in {country}:"]

        for entry in results:
            title = getattr(entry, 'title', 'Unknown Title')
            year = getattr(entry, 'release_year', 'N/A')
            obj_type = getattr(entry, 'object_type', 'MOVIE')

            providers = []
            if hasattr(entry, 'offers') and entry.offers:
                for offer in entry.offers:
                    if offer.package and offer.package.name:
                        providers.append(offer.package.name)

            prov_str = ", ".join(set(providers)) if providers else "Various"
            response_lines.append(f"- **{title}** ({year}) [{obj_type}] on {prov_str}")

        return "\n".join(response_lines)
    except Exception as e:
        return f"An error occurred while fetching popular releases: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8101)
