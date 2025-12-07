#!/usr/bin/env python3
import os
from fastmcp import FastMCP
from imap_tools import MailBox, AND
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

@mcp.tool
async def mailboxes_status(directory:str) -> dict[str, int]:
    """Get the status of a mailbox
       Return the number of messages in the mailbox,
       and the number of recent messages and unseen message

    Args:
        directory: mailbox to get the status

    Return a status like:
        { 'MESSAGES': 41, 'RECENT': 0, 'UNSEEN': 5 }
    """

    status = mailbox.folder.status(directory)

    return { 'MESSAGES': status['MESSAGES'], 'RECENT': status['RECENT'], 'UNSEEN': status['UNSEEN'] }

@mcp.tool
async def search(directory:str = 'INBOX', criteria:str = 'ALL') -> list:
    """Search for messages in a given mailbox with given criteria
       Return a list of message ids

    Args:
        directory: mailbox to get the list, search doesn't include child folders
        criteria: a string containing criteria to search the messages

        directory can be like "INBOX" for the inbox, "Sent" for sent emails,
        "Drafts" for draft emails, "Trash" for trashed email; you can get the
        list with list_mailboxes("", "*")

        Possible criteria:
            ALL                     all emails
            ANSWERED/UNANSWERED     with/without the Answered flag
            SEEN/UNSEEN             with/without the Seen flag
            FLAGGED/UNFLAGGED       with/without the Flagged flag
            DRAFT/UNDRAFT           with/without the Draft flag
            DELETED/UNDELETED       with/without the Deleted flag
            NEW/OLD                 with/without the recent flag
            FROM "email"            with email address in the FROM field
            TO "email"              with email address in the TO field
            SUBJECT "subject"       with subject in the SUBJECT field
            BODY "string"           with string in the BODY of the message
            TEXT "string"           with string in the HEADER or the BODY
            BCC "email"             with email in the BCC field
            CC "email"              with email in the CC field
            ON DD-MM-YYYY           with internal date is within DD-MM-YYYY day
                                    (DD-MM-YYYY is RFC2822 date, i.e. 15-Mar-2000)
            SINCE DD-MM-YYYY        with internal date is within or later DD-MM-YYYY
            BEFORE DD-MM-YYYY       with internal date os earlier than DD-MM-YYYY
            SENTON DD-MM-YYYY       header is within the specified date
            SENTSINCE DD-MM-YYYY    header is within or later than the specified date
            SENTBEFORE DD-MM-YYYY   header is earlier than the specified date
            LARGER SIZE             size is larger than SIZE in bytes
            SMALLER SIZE            size is smaller than SIZE in bytes
            HEADER "tag" "string"   header tag contains string
            X-GM-LABELS "string"    have this gmail label
            UID uid_list            have have an uid in the uid_list (like 1,2,23)

        Criteria are combined with AND/OR/NOT in IMAP prefix form:

            - AND is implicit: writing `SEEN UNANSWERED` means SEEN AND
              UNANSWERED.
            - NOT only negates the next search key: `NOT ON 01-Jan-2025`
              excludes that day; add further keys after it to AND them.
            - OR is binary: `OR FROM "a@example" FROM "b@example"` matches
              either sender. To OR more than two terms, nest: `OR FROM "a"
              OR FROM "b" FROM "c"`. Any criteria after the OR chain are ANDed
              with the result (e.g., `OR FROM "a" FROM "b" TO "list@x.com"`).

    Notes:
        Sent emails are in the "Sent" mailbox
        Draft emails are in "Drafts" mailbox
        Deleted emails are in "Trash" mailbox
        UIDs are only valid relatively to the giver directory
        Sent, Draft, Trash are at root level, not undex INBOX/

    Return a list like:
        [ '250735', '250737', '250738', '250739', '250743', '250747', '250755']
    """

    current_folder = mailbox.folder.get()

    mailbox.folder.set(directory)

    uids = mailbox.uids(criteria)

    mailbox.folder.set(current_folder)

    return uids

def get_message(directory: str, uid: str):
    """Read message for the given uid in directory

    Args:
        directory: directory to read from
        uid: uid of the message to read

    Return:
        the message
    """

    current_folder = mailbox.folder.get()
    try:
        mailbox.folder.set(directory)
        # Materialize the generator before switching folders back to avoid lazy fetch issues.
        mails = list(mailbox.fetch(f'UID {uid}', mark_seen=False))
    finally:
        mailbox.folder.set(current_folder)

    return mails

@mcp.tool
async def get_header(directory: str, uid: str) -> dict:
    """Read message header for the given uid in directory

    Args:
        directory: directory to read from
        uid: uid of the message to read

    Return:
        A dict of fields of RFC2822 message header
    """

    message = get_message(directory, uid)

    if message:
        return message[0].headers

    return {}

@mcp.tool
async def get_text(directory: str, uid: str) -> str:
    """Read message text for the given uid in directory

    Args:
        directory: directory to read from
        uid: uid of the message to read

    Return:
        A dict of fields of RFC2822 message header
    """

    message = get_message(directory, uid)

    if message:
        return message[0].text

    return {}

@mcp.tool
async def get_html(directory: str, uid: str) -> str:
    """Read message html for the given uid in directory

    Args:
        directory: directory to read from
        uid: uid of the message to read

    Return:
        A dict of fields of RFC2822 message header
    """

    message = get_message(directory, uid)

    if message:
        return message[0].html

    return {}

@mcp.tool
async def get_size(directory: str, uid: str) -> int:
    """Read message size for the given uid in directory

    Args:
        directory: directory to read from
        uid: uid of the message to read

    Return:
        A dict of fields of RFC2822 message header
    """

    message = get_message(directory, uid)

    if mails:
        return mails[0].size

    return 0

if __name__ == "__main__":
    mcp.run(transport='stdio')
