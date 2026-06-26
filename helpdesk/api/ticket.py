import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from helpdesk.utils import agent_only


@frappe.whitelist()
def get_customer_ticket_stats() -> dict:
    """Ticket stats for the customer portal home page.

    Scoped exactly like the portal Tickets list: HD Ticket's permission_query
    limits results to the signed-in user's own tickets plus every ticket
    belonging to the customer organisation(s) they are a contact of. Using
    frappe.get_list (not get_all) is what enforces that permission query.
    """
    tickets = frappe.get_list(
        "HD Ticket",
        fields=["status", "status_category", "resolution_date"],
        limit_page_length=0,
    )
    cutoff = add_days(getdate(nowdate()), -30)
    total = len(tickets)
    open_count = sum(1 for t in tickets if t.status_category != "Resolved")
    replied = sum(1 for t in tickets if t.status == "Replied")
    resolved_30d = sum(
        1
        for t in tickets
        if t.status_category == "Resolved"
        and t.resolution_date
        and getdate(t.resolution_date) >= cutoff
    )
    return {
        "total": total,
        "open": open_count,
        "replied": replied,
        "resolved_30d": resolved_30d,
    }


@frappe.whitelist()
@agent_only
def bulk_reply(ticket_ids: list, message: str, attachments: list | None = None):

    link_attachments_to_tickets(attachments, ticket_ids)

    if not ticket_ids:
        return

    ticket_ids = list(set(ticket_ids))  # Remove duplicates

    for ticket_id in ticket_ids:
        frappe.has_permission("HD Ticket", "write", doc=ticket_id, throw=True)
        doc = frappe.get_doc("HD Ticket", ticket_id)
        try:
            doc.reply_via_agent(
                message, to=doc.raised_by, attachments=attachments or []
            )
        except Exception as e:
            frappe.log_error(
                title=f"Bulk reply failed for ticket {ticket_id}",
                message=str(e),
            )


def link_attachments_to_tickets(attachments: list | None, ticket_ids: list):
    if not attachments:
        return
    if not ticket_ids:
        return

    # only one attachment is created, but does not refer to any doctype/docname until now. Link it to all the tickets in context.
    # Done because, FileUploader only handles for one file, and cant upload to multiple doctypes/docnames at the same time.
    for a in attachments:
        file_doc = frappe.get_doc("File", a)
        file_doc.attached_to_doctype = "HD Ticket"
        file_doc.attached_to_name = ticket_ids[0]
        file_doc.save()

    for ticket_id in ticket_ids[1:]:
        for a in attachments:
            file_doc = frappe.get_doc("File", a)
            new_file_doc = frappe.copy_doc(file_doc)
            new_file_doc.attached_to_name = ticket_id
            new_file_doc.save()


def assign_ticket_to_agent(ticket_id, agent_id=None):
    if not ticket_id:
        return

    ticket_doc = frappe.get_doc("HD Ticket", ticket_id)

    if not agent_id:
        # assign to self
        agent_id = frappe.session.user

    if not frappe.db.exists("HD Agent", agent_id):
        frappe.throw(_("Tickets can only be assigned to agents"))

    ticket_doc.assign_agent(agent_id)
    return ticket_doc
