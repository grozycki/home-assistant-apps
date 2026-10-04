from logging import Logger
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.transforms import ResourcesAsTools


def register_app_resources(mcp: FastMCP, logger: Logger) -> None:
    guides_dir = Path("/guides")

    @mcp.resource("app://guide/{package_name}")
    def get_app_guide(package_name: str) -> str:
        """
        Provides specific UI navigation quirks, limitations, and fallback strategies
        for Android TV applications by reading markdown files from the guides directory.
        """
        logger.info(f"App navigation guide requested for package: {package_name}")

        safe_filename = "".join([c for c in package_name if c.isalnum() or c in ('_', '-', '.')])
        file_path = guides_dir / f"{safe_filename}.md"

        if file_path.exists() and file_path.is_file():
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception as e:
                return f"Error reading guide for {package_name}: {e}"

        return f"No specialized navigation guide available for package '{package_name}'."

    mcp.add_transform(ResourcesAsTools(mcp))
