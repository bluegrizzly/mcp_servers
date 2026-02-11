# Jira MCP Server

MCP server for [Jira Cloud REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/). Lets agents create issues, search and read issues, and run reports by status.

## Tools

| Tool | Description |
|------|-------------|
| **jira_create_issue** | Create a new issue (project, summary, type, optional description and priority). |
| **jira_get_issue** | Get a single issue by key (e.g. `PROJ-123`), with optional field list. |
| **jira_search_issues** | Search issues with JQL; pagination via `start_at` and `max_results`. |
| **jira_issue_count** | Approximate count for a JQL query. JQL must be *bounded* (e.g. `project = PROJ` or `filter = 12345`). |
| **jira_issues_report** | Report by status: pass a project key or JQL; returns issue list and counts per status. |

## Setup

1. **Environment variables** (required):

   - `JIRA_BASE_URL` – Jira Cloud base URL, e.g. `https://your-site.atlassian.net`
   - `JIRA_EMAIL` – Your Atlassian account email
   - `JIRA_API_TOKEN` – [API token](https://id.atlassian.com/manage-profile/security/api-tokens) (Basic auth)

2. **Install and run** (from repo root, with Python 3.11+):

   ```bash
   cd jira-server
   uv sync
   uv run python main.py
   ```

   Or add the server to your MCP config (e.g. Cursor) with `uv run python main.py` and the env vars set.

## Example JQL for search and reports

For **jira_issue_count**, JQL must be bounded (include `project = ...` or `filter = ...`).

- `project = MYPROJ` – all issues in project
- `project = MYPROJ AND status = 'In Progress'` – by status
- `assignee = currentUser()` – my issues
- `summary ~ "login"` – text in summary
- `created >= -7d` – created in last 7 days
