#!/usr/bin/env python3
import os
import sys
import datetime
from fastmcp import FastMCP
from fastmcp.prompts.prompt import Message, PromptMessage, TextContent
from imap_tools import MailBox
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_LOGIN = os.getenv("IMAP_LOGIN")

missing_env = [name for name, value in {
    "IMAP_HOST": IMAP_HOST,
    "IMAP_LOGIN": IMAP_LOGIN,
}.items() if not value]

if missing_env:
    sys.exit(f"Missing required environment variables: {', '.join(missing_env)}")

IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
IMAP_TOKEN = os.getenv("IMAP_TOKEN")

mcp = FastMCP("mailbox")

def connect_IMAP() -> MailBox:
    """Create a fresh IMAP connection and authenticate."""
    if IMAP_PASSWORD is not None:
        return MailBox(IMAP_HOST).login(IMAP_LOGIN, IMAP_PASSWORD)
    elif IMAP_TOKEN is not None:
        return MailBox(IMAP_HOST).xoauth2(IMAP_LOGIN, IMAP_TOKEN)
    else:
        return None

def check_IMAP():
    """Check the IMAP connection is alive; reconnect if needed."""
    global mailbox
    try:
        # NOOP validates the socket without changing state
        mailbox.client.noop()
    except:
        try:
            mailbox.logout()
        except Exception:
            pass
        mailbox = connect_IMAP()

@mcp.prompt
def list_patches_of_a_series(cover_letter: str) -> str:
    """Generates a user message to list the patches of the series of a given cover letter,
       i.e [PATCH 0/X], provides [PATCH 1/X] to [PATCH X/X]
    """
    return f'Search emails with In-Reply-To equal to Message-ID of {cover_letter}'

@mcp.prompt
def review_a_patch_series() -> str:
    """Generates a user message how to do a review on a patch series"""
    return "When replying to reviews or patch series: reply to each message individually, include the full original message inline, and place your comment directly beneath the specific line you are annotating. Format your answer on 80 columns"

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
                   if empty - get from root, includes "Sent", "Trash", "Drafts", "Junk", ...
        pattern:   glob-like match for names directory (e.g., "*" for all children, 
                   and for instance "Archives*" to match all archives folders
                   * is a wildcard, and matches zero or more characters at this position
                   % is similar to * but it does not match a hierarchy delimiter

    Examples:
        - All inbox folders: list_mailboxes("", "*")
        - Only Archives tree: list_mailboxes("Archives")
        - Root-level folders starting with “Q”: list_mailboxes("INBOX", "Q*").

    Return:
        return a list of mailboxes, in the form of a list of key and value:
        PATH for the full path, DELIMITER for the patch delimiter and FLAGS
        for the list of the flags of the mailbox.

        Flags (RFC 6154):
            \\HasNoChildren     mailbox has no child mailbox
            \\Sent              mailbox is the Sent mailbox
            \\Junk              mailbox is the Junk mailbox
            \\Drafts            mailbox is the Drafts mailbox
            \\Flagged           mailbox presents all messages marked in some way as "important"
            \\Archive           mailbox is used to archive messages
            \\All               mailbox presents all messages in the user's message store
            \\Trash             mailbox is the Trash mailbox
                                In some server implementations, this might be a virtual mailbox,
                                containing messages from other mailboxes that are marked with
                                the "\\Deleted" message flag.
    Notes:
        - Paths in results are absolute from the root (so use INBOX/...).
    """

    mailboxes = [ ]
    check_IMAP()
    for f in mailbox.folder.list(folder=directory, search_args=pattern):
        mailboxes.append( { 'PATH': f.name,
                            'DELIMITER': f.delim,
                            'FLAGS': [ flag for flag in f.flags ]
                           } )
    
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

    check_IMAP()
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
        Full text search is not supported
        Never provides message ids (uid) to the user, they are not useful
        for him

    Return a list like:
        [ '250735', '250737', '250738', '250739', '250743', '250747', '250755']
    """

    check_IMAP()
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
        uids: an array of UID strings
        headers_only: if True, fetch only headers to avoid downloading bodies

    Return:
        list of message object
    """

    check_IMAP()
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
        uids: an array of UID strings

    Return:
        List of dict of header names to list of values

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
        uids: an array of UID strings

    Return:
        list of plain text body
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
        uids: an array of UID strings

    Return:
        list of HTML body
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
        uids: an array of UID strings

    Return:
        list of message size in bytes
    """

    messages = get_messages(directory, uids, headers_only=True)

    sizes = [ ]
    for message in messages:
        sizes.append(message.size_rfc822)

    return sizes

@mcp.tool
async def create_message(content: str, date: str | None = None):
    """Create a message in Drafts folder

    Args:
        content: raw content of the mail
        date: optional ISO-8601 datetime string used for the IMAP APPEND timestamp

    Return:
        dict containing IMAP append status and server data (bytes decoded to str)

    Notes:
        In the header, use the current date and time
        Check the date in the header before calling create_message
        If the message is a reply to another one, its "In-Reply-To" header
        must contain the "Message-ID" of the original message.
    """

    check_IMAP()

    # imap_tools.append expects RFC 822 bytes; encode the provided text as UTF-8.
    status, data = mailbox.append(content.encode("utf-8"), 'Drafts')

    # imaplib returns a list of bytes; convert to strings for JSON friendliness.
    decoded_data = [
        item.decode("utf-8", errors="replace") if isinstance(item, (bytes, bytearray)) else item
        for item in data or []
    ]

    return {"status": status, "data": decoded_data}

mailbox = connect_IMAP()
if mailbox == None:
    sys.exit(1)
    
if __name__ == "__main__":
    mcp.run(transport='stdio')
