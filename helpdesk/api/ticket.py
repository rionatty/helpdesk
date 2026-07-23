import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from helpdesk.utils import agent_only


@frappe.whitelist()
@agent_only
def get_helpdesk_email_addresses() -> list:
	"""The helpdesk's ticket-ingesting inbox addresses. Used by the reply
	composer so replies never To/Cc the helpdesk itself (mail loops).
	Deliberately NOT every site Email Account: a personal mailbox that has
	an Email Account is a valid recipient."""
	from helpdesk.helpdesk.utils.email import ticket_ingest_addresses

	return sorted(ticket_ingest_addresses())


@frappe.whitelist()
def close_automated_backlog(dry_run: bool = True) -> dict:
	"""One-time queue cleanup: close every not-yet-resolved email-channel
	ticket whose requester matches the automated-sender patterns (HD
	Settings). Run with dry_run=1 first — it only lists what WOULD close.
	No emails are sent for these closures (the status-change email skips
	automated requesters). Manager-only."""
	frappe.only_for(["Agent Manager", "System Manager"])
	from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import HDTicket

	open_statuses = frappe.get_all(
		"HD Ticket Status", filters={"category": ["!=", "Resolved"]}, pluck="name"
	)
	candidates = frappe.get_all(
		"HD Ticket",
		filters={
			"status": ["in", open_statuses],
			"via_customer_portal": 0,
		},
		fields=["name", "raised_by", "status", "subject"],
	)
	matched = [
		t
		for t in candidates
		if HDTicket._sender_matches_automated_patterns(t.raised_by)
	]
	closed, failed = [], []
	if not dry_run:
		closed_status = frappe.db.get_single_value(
			"HD Settings", "auto_close_status"
		) or frappe.db.get_value("HD Ticket Status", {"category": "Resolved"}, "name")
		for t in matched:
			try:
				doc = frappe.get_doc("HD Ticket", t.name)
				doc.status = closed_status
				doc.flags.ignore_validate = True
				doc.save(ignore_permissions=True)
				closed.append(t.name)
			except Exception:
				failed.append(t.name)
				frappe.log_error(
					title=f"Automated-backlog close failed for {t.name}"
				)
	return {
		"dry_run": bool(dry_run),
		"would_close" if dry_run else "closed": [
			{"ticket": t.name, "from": t.raised_by, "subject": t.subject}
			for t in matched
		],
		"count": len(matched),
		"failed": failed,
	}


@frappe.whitelist()
@agent_only
def resend_communication_email(communication: str) -> dict:
	"""Requeue a helpdesk reply email that failed (or got stuck) at SMTP,
	and try to push it out immediately; the email-flush worker is the
	fallback. Used by the Resend button on the conversation's Error chip."""
	ref_doctype = frappe.db.get_value(
		"Communication", communication, "reference_doctype"
	)
	if ref_doctype != "HD Ticket":
		frappe.throw(_("Not a helpdesk communication"))
	rows = frappe.get_all(
		"Email Queue",
		filters={"communication": communication},
		fields=["name"],
		order_by="creation desc",
		limit_page_length=1,
	)
	if not rows:
		frappe.throw(
			_("No email record exists for this message — use Reply instead.")
		)
	queue = frappe.get_doc("Email Queue", rows[0].name)
	queue.db_set("status", "Not Sent")
	queue.db_set("error", None)
	try:
		queue.reload()
		queue.send()
		return {"status": "sent"}
	except Exception:
		# Version differences / SMTP hiccup: leave it queued for the
		# scheduler's email flush instead of failing the request.
		frappe.log_error(
			title=f"Immediate resend failed for {queue.name}; left queued"
		)
		return {"status": "queued"}


@frappe.whitelist()
@agent_only
def diagnose_ticket_email(ticket: str) -> dict:
	"""One-shot answer to 'why didn't the reply email go out?' — the settings
	gates, the outgoing accounts, and the actual Email Queue rows for this
	ticket with their real SMTP status/error. Agent-only."""
	settings = frappe.get_single("HD Settings")
	outgoing = frappe.get_all(
		"Email Account",
		filters={"enable_outgoing": 1},
		fields=["name", "email_id", "default_outgoing"],
	)
	comms = frappe.get_all(
		"Communication",
		filters={"reference_doctype": "HD Ticket", "reference_name": ticket},
		pluck="name",
	)
	queue = []
	recipients_status = []
	if comms:
		queue = frappe.get_all(
			"Email Queue",
			filters={"communication": ["in", comms]},
			fields=["name", "status", "error", "creation"],
			order_by="creation desc",
			limit_page_length=10,
		)
		if queue:
			recipients_status = frappe.get_all(
				"Email Queue Recipient",
				filters={"parent": ["in", [q.name for q in queue]]},
				fields=["parent", "recipient", "status", "error"],
				parent_doctype="Email Queue",
			)
	from helpdesk.helpdesk.utils.email import ticket_ingest_addresses

	ticket_ingest_addresses_set = ticket_ingest_addresses()
	requester = frappe.db.get_value("HD Ticket", ticket, "raised_by")
	unsubscribed = (
		frappe.get_all(
			"Email Unsubscribe",
			filters={"email": requester},
			fields=[
				"name",
				"email",
				"global_unsubscribe",
				"reference_doctype",
				"reference_name",
			],
		)
		if requester
		else []
	)
	return {
		"gates": {
			"skip_email_workflow": settings.get("skip_email_workflow"),
			"enable_reply_email_via_agent": settings.get(
				"enable_reply_email_via_agent"
			),
			"send_acknowledgement_email": settings.get("send_acknowledgement_email"),
			"mute_emails_site_config": bool(
				frappe.conf.get("mute_emails") or frappe.flags.mute_emails
			),
		},
		"requester": requester,
		"requester_unsubscribed": unsubscribed,
		"outgoing_accounts": outgoing,
		"ticket_ingest_addresses": sorted(ticket_ingest_addresses_set),
		"requester_is_ingest_address": bool(
			requester and requester.lower() in ticket_ingest_addresses_set
		),
		"has_default_outgoing": any(a.default_outgoing for a in outgoing),
		"email_queue_for_ticket": queue,
		"email_queue_recipients": recipients_status,
		"note": (
			"If email_queue_for_ticket is empty, replies are being blocked by a "
			"settings gate, mute_emails, or an unsubscribe row (a 'Sent' "
			"Communication is created regardless). requester_unsubscribed rows "
			"mean frappe silently DROPS that address — new replies now clear "
			"these automatically. If a row shows status Error, its 'error' "
			"field is the SMTP reason. If status Sent, the mail was accepted "
			"by SMTP — check the recipient's spam folder."
		),
	}


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
