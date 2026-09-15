from email.utils import parseaddr

import frappe
from frappe.query_builder import DocType, Query

# Local parts mail systems use for bounce / delivery-failure mail
# (MAILER-DAEMON, postmaster, qmail's double-bounce). Matched exactly, so
# real people — sarah.labounce@…, postmaster.jones@… — are never caught.
BOUNCE_LOCAL_PARTS = frozenset(
    {
        "mailer-daemon",
        "mailerdaemon",
        "mailer_daemon",
        "mail-daemon",
        "maildaemon",
        "postmaster",
        "double-bounce",
    }
)
# Exchange / Microsoft 365 non-delivery reports come from this system mailbox.
EXCHANGE_NDR_LOCAL_PREFIX = "microsoftexchange329e71ec88ae4615bbc36ab6ce41109e"


def is_bounce_address(email: str | None) -> bool:
    """Whether `email` belongs to a mail system's bounce machinery."""
    if not email:
        return False
    address = (parseaddr(email)[1] or email).strip().lower()
    local = address.split("@", 1)[0].split("+", 1)[0]
    return local in BOUNCE_LOCAL_PARTS or local.startswith(EXCHANGE_NDR_LOCAL_PREFIX)


def is_delivery_failure_report(msg) -> bool:
    """Whether a parsed email message is a bounce, recognised by structure
    rather than by sender: an RFC 3464 report (multipart/report;
    report-type=delivery-status) or the X-Failed-Recipients header exim and
    others add. People's mail never carries either."""
    try:
        if msg is None:
            return False
        if msg.get("X-Failed-Recipients"):
            return True
        return (
            msg.get_content_type() == "multipart/report"
            and str(msg.get_param("report-type") or "").lower() == "delivery-status"
        )
    except Exception:
        return False


def is_automated_inbound_mail(msg, from_email: str | None) -> bool:
    """RFC 3834 §2: mail that must never receive an automatic response —
    bounces, anything marked Auto-Submitted, our own auto-generated mail,
    and bulk/list/junk precedence. Answering these is how mail loops start."""
    if is_bounce_address(from_email) or is_delivery_failure_report(msg):
        return True
    try:
        if msg is None:
            return False
        auto_submitted = (msg.get("Auto-Submitted") or "").strip().lower()
        if auto_submitted and auto_submitted != "no":
            return True
        if msg.get("X-Auto-Generated"):
            return True
        precedence = (msg.get("Precedence") or "").strip().lower()
        return precedence in ("bulk", "junk", "list", "auto_reply")
    except Exception:
        return False


def query_get_one(q: Query) -> dict:
    r = q.run(as_dict=True)

    if len(r) != 1:
        return

    return r.pop()


def default_outgoing_email_account():
    QBEmailAccount = DocType("Email Account")

    r = (
        frappe.qb.from_(QBEmailAccount)
        .select(QBEmailAccount.star)
        .where(QBEmailAccount.default_outgoing == 1)
        .limit(1)
    )

    return query_get_one(r)


def default_ticket_outgoing_email_account():
    QBEmailAccount = DocType("Email Account")
    QBImapFolder = DocType("IMAP Folder")

    r = (
        frappe.qb.from_(QBEmailAccount)
        .select(QBEmailAccount.star)
        .where(QBEmailAccount.default_outgoing == 1)
        .inner_join(QBImapFolder)
        .on(QBImapFolder.parent == QBEmailAccount.name)
        .where(QBImapFolder.append_to == "HD Ticket")
        .limit(1)
    )

    return query_get_one(r)


def ticket_ingest_addresses() -> set:
    """Lower-cased addresses of Email Accounts that ingest mail into the
    helpdesk — append_to 'HD Ticket' directly or via an IMAP folder.
    Emailing one of these from a reply loops the reply back in as a new
    ticket, so these (and only these) must never be reply recipients.
    A personal address that merely has an Email Account on the site is a
    perfectly valid recipient."""
    accounts = frappe.get_all(
        "Email Account",
        filters={"enable_incoming": 1},
        fields=["name", "email_id", "append_to"],
    )
    imap_hd_parents = set(
        frappe.get_all(
            "IMAP Folder", filters={"append_to": "HD Ticket"}, pluck="parent"
        )
    )
    return {
        a.email_id.lower()
        for a in accounts
        if a.email_id and (a.append_to == "HD Ticket" or a.name in imap_hd_parents)
    }
