#!/usr/bin/env python3
import os
import sys
from fastmcp import FastMCP
from imap_tools import MailBox
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_LOGIN = os.getenv("IMAP_LOGIN")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

missing_env = [name for name, value in {
    "IMAP_HOST": IMAP_HOST,
    "IMAP_LOGIN": IMAP_LOGIN,
    "IMAP_PASSWORD": IMAP_PASSWORD,
}.items() if not value]

if missing_env:
    sys.exit(f"Missing required environment variables: {', '.join(missing_env)}")

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

    IMAP4 prefix-form search criteria (RFC 3501):

        Criteria are written in prefix (Polish) notation. Multiple criteria at the same
        level are implicitly combined with AND. OR and NOT are explicit. Parentheses
        group search keys.

        AND (implicit):
            Listing criteria in sequence means all must match.
                SEEN UNANSWERED FLAGGED
            is interpreted as:
                SEEN AND UNANSWERED AND FLAGGED

        NOT:
            Negates a single search key, which may itself be a parenthesized group.
                NOT ON 01-Jan-2025
            matches messages not from that date.
                NOT (SEEN UNANSWERED FLAGGED)
            matches messages that are not simultaneously seen, unanswered and flagged.

        OR:
            OR takes exactly two search keys:
                OR FROM "a@example" FROM "b@example"
            matches messages from either a@example or b@example.

            To OR more than two conditions, nest OR:
                OR FROM "a@example" OR FROM "b@example" FROM "c@example"
            matches messages from a@example, b@example or c@example.

            Additional criteria after an OR are AND-ed:
                OR FROM "a@example" FROM "b@example" ON 01-Jan-2025
            means:
                (FROM "a@example" OR FROM "b@example") AND ON 01-Jan-2025

    Parentheses:
        Used to group search keys (for AND, OR, and NOT).
            (SEEN UNANSWERED FLAGGED)
        is an AND group.

            NOT (OR FROM "boss@example" FROM "hr@example")
        matches messages not from boss@example and not from hr@example.

    Notes:
        Sent emails are in the "Sent" mailbox
        Draft emails are in "Drafts" mailbox
        Deleted emails are in "Trash" mailbox
        UIDs are only valid relatively to the given directory
        Sent, Draft, Trash are at root level, not undex INBOX/

    Return a list like:
        [ '250735', '250737', '250738', '250739', '250743', '250747', '250755']
    """

    current_folder = mailbox.folder.get()

    try:
        mailbox.folder.set(directory)
        uids = mailbox.uids(criteria, charset="utf8")
    finally:
        mailbox.folder.set(current_folder)

    return uids

def get_messages(directory: str, uids: list, headers_only: bool = True) -> list:
    """Read message for the given uid in directory

    Args:
        directory: directory to read from
        uids: list of uids of the messages to read
        headers_only: if True, fetch only headers to avoid downloading bodies

    Return:
        single message object or None if not found
    """

    current_folder = mailbox.folder.get()

    try:
        mailbox.folder.set(directory)
        # Consume the generator before restoring the previous folder to ensure
        # fetch calls target the intended mailbox.
        messages = list(
            mailbox.fetch(
                f'UID {",".join(uids)}',
                mark_seen=False,
                headers_only=headers_only,
                charset="utf8"
            )
        )
    finally:
        mailbox.folder.set(current_folder)

    return messages

@mcp.tool
async def get_header(directory: str, uids: list) -> list:
    """Read message header for the given uid in directory

    Args:
        directory: directory to read from
        uids: list of uids of the messages to read

    Return:
        Dict of header names to list of values

    Notes: charset is utf-8
    """

    messages = get_messages(directory, uids, headers_only=True)

    headers = [ ]
    for message in messages:
        # Convert tuple values to lists for JSON friendliness.
        headers.append( {key: list(values) for key, values in message.headers.items()})

    return headers

@mcp.tool
async def get_text(directory: str, uids: list) -> list:
    """Read plain text body for the given uid in directory

    Args:
        directory: directory to read from
        uids: list of uids of the messages to read

    Return:
        Plain text body, empty string if not found
    Notes: charset is utf-8
    """

    messages = get_messages(directory, uids, headers_only=False)

    texts = [ ]
    for message in messages:
        texts.append(message.text)

    return texts

@mcp.tool
async def get_html(directory: str, uids: str) -> list:
    """Read HTML body for the given uid in directory

    Args:
        directory: directory to read from
        uids: list of uids of the messages to read

    Return:
        HTML body, empty string if not found
    Notes: charset is utf-8
    """

    messages = get_messages(directory, uids, headers_only=False)

    html = [ ]
    for message in messages:
        html.append(message.html)

    return html

@mcp.tool
async def get_size(directory: str, uids: list) -> list:
    """Read message size for the given uid in directory

    Args:
        directory: directory to read from
        uids: list of uids of the messages to read

    Return:
        Message size in bytes, 0 if not found
    """

    messages = get_messages(directory, uids, headers_only=True)

    sizes = [ ]
    for message in messages:
        sizes.append(message.size_rfc822)

    return sizes

if __name__ == "__main__":
    mcp.run(transport='stdio')
