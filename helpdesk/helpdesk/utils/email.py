import frappe
from frappe.query_builder import DocType, Query


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
