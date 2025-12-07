# imap-mcp-server

Minimal MCP server that bridges an MCP-capable agent to an IMAP mailbox. The server exposes a handful of mailbox utilities over the MCP protocol using `fastmcp` and `imap_tools`, letting an agent inspect folders and search messages without direct IMAP handling.

## Available tools
- `whoami()`: return the configured IMAP login/email address.
- `list_mailboxes(directory, pattern)`: enumerate folders matching an IMAP glob pattern.
- `mailboxes_status(directory)`: fetch `MESSAGES`, `RECENT`, and `UNSEEN` counts for a folder.
- `search(directory="INBOX", criteria="ALL")`: run an IMAP search in a folder and return matching UIDs.

## Setup
1) (Recommended) `python3 -m venv .venv` and `source .venv/bin/activate`
2) Install dependencies: `python3 -m pip install -r requirements.txt`

## Configuration
Set these environment variables (a `.env` file is supported via `python-dotenv`):
- `IMAP_HOST`: IMAP server hostname.
- `IMAP_LOGIN`: username/email for login.
- `IMAP_PASSWORD`: password or app-specific password for login.

## Run

Use "clause mcp add mailbox ./mcp-server.py" or "codex mcp add mailbox ./mcp-server.py"

## License
Distributed under the GNU General Public License v2.0. See `LICENSE` for details.
