

# Wikipedia MCP Server using MCP Python SDK (FastMCP interface)
from typing import Any
import requests
from mcp.server.fastmcp import FastMCP

WIKIPEDIA_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"

def get_wikipedia_summary_with_redirect(page: str) -> dict[str, Any]:
    """Fetch summary for a Wikipedia page with redirect support."""
    url = WIKIPEDIA_API_URL + requests.utils.quote(page) + "?redirect=true"
    headers = {
            "Accept": "application/json",
            "User-Agent": "WikipediaMCP/1.0 (https://github.com/AndyFire/mcp_servers/wikipedia-server)"
        }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": f"Wikipedia API error: {resp.status_code}", "detail": resp.text}
def get_wikipedia_summary(subject: str) -> dict[str, Any]:
    """Fetch summary for a subject from Wikipedia REST API."""
    url = WIKIPEDIA_API_URL + requests.utils.quote(subject)
    headers = {
            "Accept": "application/json",
            "User-Agent": "WikipediaMCP/1.0 (https://github.com/AndyFire/mcp_servers/wikipedia-server)"
        }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": f"Wikipedia API error: {resp.status_code}", "detail": resp.text}


# Create the MCP server instance
mcp = FastMCP("Wikipedia")

@mcp.tool()
def wikipedia_query(subject: str) -> dict[str, Any]:
    """Get a summary of a subject from Wikipedia.

    Args:
        subject: The subject or page title to look up on Wikipedia.
    Returns:
        A dictionary containing the Wikipedia summary or error details.
    """
    return get_wikipedia_summary(subject)

def main() -> None:
    mcp.run(transport="stdio")


# New tool: get summary by page name with redirect
@mcp.tool()
def wikipedia_page_summary(page: str) -> dict[str, Any]:
    """Get only the extract (summary text) of a Wikipedia page by name, following redirects.

    Args:
        page: The Wikipedia page name (title).
    Returns:
        A dictionary with only the 'extract' field or error details.
    """
    result = get_wikipedia_summary_with_redirect(page)
    if "extract" in result:
        return {"extract": result["extract"]}
    else:
        return result

if __name__ == "__main__":
    main()
