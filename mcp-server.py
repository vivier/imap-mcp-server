#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from imap_tools import MailBox
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_LOGIN = os.getenv("IMAP_LOGIN")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

mailbox = MailBox(IMAP_HOST).login(IMAP_LOGIN, IMAP_PASSWORD)

mcp = FastMCP("mailbox")

@mcp.tool
async def whoami() -> str:
    """Returns the configured email address for the current account.
       Use it to confirm which mailbox the other commands will operate on
    """
    return IMAP_LOGIN

@mcp.tool
async def list_mailboxes(directory:str, pattern:str) -> list:
    """Enumerates mailboxes under a given folder.

    Args:
        directory: base folder to search (e.g. "INBOX" for standard inbox,
                   INBOX/Trash for standard trash folder, ...)
                   if empty - get from root
        pattern:   glob-like match for names directory (e.g., "*" for all children, 
                   and for instance "Archives*" to match all archives folders
                   * is a wildcard, and matches zero or more characters at this position
                   % is similar to * but it does not match a hierarchy delimiter

    Examples:
        - All inbox folders: list_mailboxes("", "*")
        - Only Archives tree: list_mailboxes("Archives")
        - Root-level folders starting with “Q”: list_mailboxes("INBOX", "Q*").

    Notes:
        - Paths in results are absolute from the root (so use INBOX/...).
    """


    mailboxes = [ ]
    for f in mailbox.folder.list(folder=directory, search_args=pattern):
        mailboxes.append(f.name)
    
    return mailboxes

if __name__ == "__main__":
    mcp.run(transport='stdio')
