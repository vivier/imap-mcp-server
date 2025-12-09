# imap-mcp-server

Minimal MCP server that bridges an MCP-capable agent to an IMAP4 mailbox. It uses `fastmcp` with `imap-tools` to expose a handful of read-only mailbox helpers so an agent can explore folders, search, and fetch message content without speaking IMAP directly.

## Exposed tools
- `whoami()`: Return the configured login/email address.
- `list_mailboxes(directory, pattern)`: Enumerate folders using IMAP globbing.
- `mailboxes_status(directory)`: Return `MESSAGES`, `RECENT`, and `UNSEEN` counts.
- `search(directory="INBOX", criteria="ALL")`: Run an IMAP search and return matching UIDs.
- `get_header(directory, uids)`: Fetch raw headers (dict of header name to list of values) for each UID.
- `get_text(directory, uids)`: Fetch the plain text body for each UID.
- `get_html(directory, uids)`: Fetch the HTML body for each UID.
- `get_size(directory, uids)`: Fetch RFC822 message sizes in bytes.

Notes:
- UIDs are relative to the folder you query; use the same `directory` for `search` and subsequent `get_*` calls.
- Message fetches are read-only and avoid marking messages as seen.

## Requirements
- Python 3.10+
- An IMAP account with host, username, and either:
  - Password/app password (traditional authentication), or
  - OAuth2 token (for Gmail and other OAuth-enabled providers)

## Setup
1) (Recommended) `python3 -m venv .venv && source .venv/bin/activate`
2) Install dependencies: `python3 -m pip install -r requirements.txt`

## Configuration
The server reads credentials from environment variables; a `.env` file is supported via `python-dotenv`.

### Traditional IMAP Authentication
For standard IMAP servers:
```
IMAP_HOST=imap.example.com
IMAP_LOGIN=user@example.com
IMAP_PASSWORD=app-specific-password
```

### Gmail OAuth2 Authentication
For Gmail using OAuth2:
```
IMAP_HOST=imap.gmail.com
IMAP_LOGIN=user@gmail.com
IMAP_TOKEN=your-oauth2-access-token
```

To obtain a Gmail OAuth2 token:
1) Create OAuth2 credentials in Google Cloud Console
   - Enable Gmail API for your project
   - Create OAuth 2.0 Client ID (Desktop application)
   - Note your client ID and client secret
2) Run the token helper script:
   ```
   python3 gmail_auth.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
   ```
3) Follow the browser prompt to authorize access
4) Copy the `access_token` to your `.env` file as `IMAP_TOKEN`

Keep credentials out of version control and prefer app passwords or OAuth2 tokens when possible.

## Run
- Direct execution: `python mcp-server.py`
- Register with a client: `clause mcp add mailbox ./mcp-server.py` or `codex mcp add mailbox ./mcp-server.py`

Ensure you run the command in a shell where the environment variables above are set or a `.env` file is present.

## License
Distributed under the GNU General Public License v2.0. See `LICENSE` for details.
