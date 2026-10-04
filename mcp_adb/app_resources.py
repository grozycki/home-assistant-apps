from logging import Logger
from pathlib import Path

from fastmcp import FastMCP


def register_app_resources(mcp: FastMCP, logger: Logger, guides_dir: str = "guides") -> None:
    guides_path = Path(guides_dir)

    @mcp.resource("app://guide/{package_name}")
    def get_app_guide(package_name: str) -> str:
        """
        Provides specific UI navigation quirks, limitations, and fallback strategies
        for Android TV applications by reading markdown files from the guides directory.
        """
        logger.info(f"App navigation guide requested for package: {package_name}")

        safe_filename = "".join([c for c in package_name if c.isalnum() or c in ('_', '-', '.')])
        file_path = guides_path / f"{safe_filename}.md"

        if file_path.exists() and file_path.is_file():
            try:
                logger.info(f"Loading guide from file: {file_path}")
                return file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read guide file {file_path}: {e}")
                return f"Error reading navigation guide for {package_name}."

        return (
            f"No specialized navigation guide available for package '{package_name}'. "
            "Use standard Android TV navigation and check UI hierarchy if supported."
        )