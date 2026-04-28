# imap-mcp-server

Minimal MCP server that bridges an MCP-capable agent to an IMAP4 mailbox. It uses
`fastmcp` with `imap-tools` to expose mailbox helpers so an agent can explore
folders, search, fetch message content, inspect and change message keywords, and
create draft replies without speaking IMAP directly.

## Exposed tools
- `whoami()`: Return the configured login/email address.
- `list_mailboxes(directory, pattern)`: Enumerate folders using IMAP globbing.
- `mailboxes_status(directory)`: Return `MESSAGES`, `RECENT`, and `UNSEEN` counts.
- `search(directory="INBOX", criteria="ALL")`: Run an IMAP search and return matching UIDs.
- `get_header(directory, uids)`: Fetch raw headers (dict of header name to list of values) for each UID.
- `get_header_field(directory, uids, field)`: Fetch one header field for each UID.
- `get_text(directory, uids)`: Fetch the plain text body for each UID.
- `get_html(directory, uids)`: Fetch the HTML body for each UID.
- `get_size(directory, uids)`: Fetch RFC822 message sizes in bytes.
- `get_keywords(directory, uids)`: Fetch IMAP flags/keywords for each UID.
- `change_keywords(directory, uids, keywords, set)`: Add or remove IMAP flags/keywords.
- `create_message(content)`: Append a raw RFC 822 message to the `Drafts` mailbox.

Notes:
- UIDs are relative to the folder you query; use the same `directory` for `search` and subsequent `get_*` calls.
- Message fetches are read-only and avoid marking messages as seen.
- `change_keywords()` and `create_message()` modify the mailbox state.

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

Direct execution: `python mcp-server.py`

Register with a client: `clause mcp add mailbox ./mcp-server.py` or `codex mcp add mailbox ./mcp-server.py`

You can also run the MCP server using http transport:

`fastmcp run mcp-server.py -t http --host 192.168.100.1`

And then add it to codex:

`codex mcp add email --url http://192.168.100.1:8000/mcp`

Ensure you run the command in a shell where the environment variables above are set or a `.env` file is present.

## Example

```text
> Review message-id 20260424091024.23495-1-deller@kernel.org from INBOX/Qemu/linux-user
```

1. High: `[PATCH 4/4]` mis-encodes successful `_NEW` `getsockopt()` results when
   userspace passes a buffer larger than `sizeof(struct target__kernel_sock_timeval)`.
   The new branch chooses the 64-bit copy path only on exact equality; any larger
   `len` falls back to `copy_to_user_timeval()`, which writes the old layout instead.
   The decision needs to be based on `optname`, with `len` clamped via `MIN(...)`,
   not on `len == sizeof(...)`. Relevant code is in `linux-user/syscall.c:2604`.
   Source for the patch hunk:
   <https://www.mail-archive.com/qemu-devel%40nongnu.org/msg1186189.html>

2. Medium: `[PATCH 1/4]` should not replace `abi_llong` with plain `int64_t` in
   `struct target__kernel_sock_timeval`. `abi_llong` carries target ABI alignment
   requirements; `int64_t` does not, so this can change guest-visible
   layout/alignment on some targets. The current struct is at
   `linux-user/syscall_defs.h:240`. Richard Henderson already NACKed this
   point in-thread:
   <https://www.mail-archive.com/qemu-devel%40nongnu.org/msg1186340.html>

I did not find another separate functional issue in patches 2/4 or 3/4 beyond
those. If you want, I can turn this into a reply mail in the repo's preferred
quoted format.

```text
> Write replies in Draft folder
```

Two draft replies are in `Drafts`:

- `Re: [PATCH 1/4] linux-user: Use int64_t in target__kernel_sock_timeval`
- `Re: [PATCH 4/4] linux-user: Add getsockopt() for SO_RCVTIMEO_NEW and SO_SNDTIMEO_NEW`

The first calls out the target ABI alignment issue with replacing `abi_llong`,
and the second points out the `_NEW getsockopt` bug when userspace provides a
buffer larger than the 64-bit `timeval` struct.

## License

Distributed under the GNU General Public License v2.0. See `LICENSE` for details.
