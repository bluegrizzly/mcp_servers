"""
Jira Cloud MCP Server

MCP server for Jira Cloud REST API v3. Exposes tools for:
- Creating issues
- Reading and searching issues (JQL)
- Reporting and status (count by JQL, report by status)
"""

import os
import logging
from typing import Optional, Any

import httpx
from pydantic import Field
from mcp.server.fastmcp import FastMCP

# Configure logging for STDIO transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="jira-server",
    instructions="MCP server for Jira Cloud REST API v3. Create issues, search issues with JQL, get issue details, count issues, and get reports by status.",
)

# Default fields to return when searching (keeps payload small; status included for reports)
DEFAULT_SEARCH_FIELDS = "summary,status,issuetype,priority,assignee,created,updated,project"

# Jira approximate-count API requires "bounded" JQL (e.g. project, filter, issuekey)
BOUNDED_JQL_HINTS = ("project", "filter", "issuekey", "key in", "key =")
def _jql_looks_bounded(jql: str) -> bool:
    q = (jql or "").strip().lower()
    return any(hint in q for hint in BOUNDED_JQL_HINTS)


def _get_config() -> tuple[str, str, str]:
    """Return (base_url, email, api_token)."""
    base = (os.getenv("JIRA_BASE_URL") or "").rstrip("/")
    email = os.getenv("JIRA_EMAIL") or ""
    token = os.getenv("JIRA_API_TOKEN") or ""
    if not base or not email or not token:
        raise ValueError(
            "Set JIRA_BASE_URL (e.g. https://your-site.atlassian.net), "
            "JIRA_EMAIL, and JIRA_API_TOKEN. "
            "Create an API token at https://id.atlassian.com/manage-profile/security/api-tokens"
        )
    return base, email, token


def _auth() -> tuple[str, str]:
    """Basic auth (email, api_token) for Jira Cloud."""
    _, email, token = _get_config()
    return (email, token)


async def _request(
    method: str,
    path: str,
    *,
    json: Optional[dict] = None,
    params: Optional[dict] = None,
) -> dict[str, Any]:
    """Call Jira REST API v3. Path is e.g. '/rest/api/3/issue'."""
    base, _, _ = _get_config()
    url = f"{base}{path}"
    auth = _auth()
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            auth=auth,
            json=json,
            params=params,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30.0,
        )
    if resp.status_code >= 400:
        err = resp.text
        try:
            body = resp.json()
            err = body.get("errorMessages", body.get("errors", err))
        except Exception:
            pass
        raise RuntimeError(f"Jira API error {resp.status_code}: {err}")
    return resp.json() if resp.content else {}


# --- Tools ---


@mcp.tool()
async def jira_create_issue(
    project_key: str = Field(description="Project key (e.g. PROJ, MYPROJECT)"),
    summary: str = Field(description="Issue summary/title"),
    issue_type: str = Field(default="Task", description="Issue type name (e.g. Task, Bug, Story)"),
    description: Optional[str] = Field(default=None, description="Issue description (plain text)"),
    priority: Optional[str] = Field(default=None, description="Priority name (e.g. High, Medium, Low)"),
) -> dict[str, Any]:
    """
    Create a new Jira issue.
    Requires project key, summary, and optionally issue type (default Task), description, and priority.
    Returns the created issue key and id.
    """
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "issuetype": {"name": issue_type},
        "summary": summary,
    }
    if description is not None:
        fields["description"] = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]}
    if priority is not None:
        fields["priority"] = {"name": priority}
    data = await _request("POST", "/rest/api/3/issue", json={"fields": fields})
    return {"success": True, "key": data.get("key"), "id": data.get("id"), "self": data.get("self")}


@mcp.tool()
async def jira_get_issue(
    issue_key: str = Field(description="Issue key (e.g. PROJ-123)"),
    fields: Optional[str] = Field(
        default=None,
        description="Comma-separated field names to return; default returns all. e.g. summary,status,description",
    ),
) -> dict[str, Any]:
    """
    Get a single Jira issue by key.
    Optionally limit returned fields with the 'fields' parameter.
    """
    params = {}
    if fields:
        params["fields"] = fields
    path = f"/rest/api/3/issue/{issue_key}"
    data = await _request("GET", path, params=params if params else None)
    return {"success": True, "issue": data}


@mcp.tool()
async def jira_search_issues(
    jql: str = Field(description="JQL query (e.g. project = MYPROJ, status = 'In Progress', assignee = currentUser())"),
    max_results: int = Field(default=50, ge=1, le=100, description="Max issues to return (1-100)"),
    start_at: int = Field(default=0, ge=0, description="Index of first result (for pagination)"),
    fields: Optional[str] = Field(
        default=None,
        description="Comma-separated field names; default includes summary, status, issuetype, priority, assignee, created, updated, project",
    ),
) -> dict[str, Any]:
    """
    Search for issues using JQL.
    Use jql for filters (project, status, assignee, text, etc.). Paginate with start_at and max_results.
    """
    params = {"jql": jql, "maxResults": max_results, "startAt": start_at}
    if fields:
        params["fields"] = fields
    else:
        params["fields"] = DEFAULT_SEARCH_FIELDS
    data = await _request("GET", "/rest/api/3/search", params=params)
    return {
        "success": True,
        "total": data.get("total", 0),
        "startAt": data.get("startAt", 0),
        "maxResults": data.get("maxResults", 0),
        "issues": data.get("issues", []),
    }


@mcp.tool()
async def jira_issue_count(
    jql: str = Field(
        description="JQL query to count. Must be bounded: include project = KEY, filter = N, or issuekey = X (e.g. project = MYPROJ AND status = 'Open').",
    ),
) -> dict[str, Any]:
    """
    Get approximate count of issues matching a JQL query.
    Jira requires the JQL to be bounded: add a restriction like project = YOURPROJECT or filter = 12345.
    Useful for reports (e.g. count per status by calling with different JQL).
    """
    if not _jql_looks_bounded(jql):
        raise ValueError(
            "Jira requires a bounded JQL query for count. "
            "Add a restriction such as: project = YOURPROJECT or filter = 12345."
        )
    data = await _request("POST", "/rest/api/3/search/approximate-count", json={"jql": jql})
    return {"success": True, "count": data.get("count", 0), "jql": jql}


@mcp.tool()
async def jira_issues_report(
    project_key: Optional[str] = Field(default=None, description="Project key to report on (e.g. PROJ)"),
    jql: Optional[str] = Field(
        default=None,
        description="Optional JQL to filter (e.g. assignee = currentUser()). If set, project_key is ignored.",
    ),
    max_results: int = Field(default=100, ge=1, le=500, description="Max issues to fetch for aggregation (1-500)"),
) -> dict[str, Any]:
    """
    Report on issues aggregated by status.
    Provide either project_key (report for that project) or jql (custom filter).
    Returns total count, list of issues with key/summary/status, and counts per status.
    """
    if jql:
        q = jql
    elif project_key:
        q = f"project = {project_key}"
    else:
        raise ValueError("Provide either project_key or jql")
    params = {"jql": q, "maxResults": max_results, "startAt": 0, "fields": "summary,status,issuetype,created,updated"}
    data = await _request("GET", "/rest/api/3/search", params=params)
    issues = data.get("issues", [])
    total = data.get("total", 0)
    by_status: dict[str, int] = {}
    rows = []
    for i in issues:
        key = i.get("key", "?")
        fields = i.get("fields") or {}
        status_obj = fields.get("status") or {}
        status_name = status_obj.get("name", "Unknown")
        by_status[status_name] = by_status.get(status_name, 0) + 1
        rows.append({
            "key": key,
            "summary": (fields.get("summary") or ""),
            "status": status_name,
            "issuetype": (fields.get("issuetype") or {}).get("name"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
        })
    return {
        "success": True,
        "total": total,
        "count_by_status": by_status,
        "issues": rows,
    }


def main() -> None:
    try:
        _get_config()
        logger.info("Jira config found, starting server")
    except ValueError as e:
        logger.error("Config error: %s", e)
        raise
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
