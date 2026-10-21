# Copyright (c) 2026, rionatty and contributors
# Telling the customer's team where their ticket has got to.
#
# Resolved and closed have their own, fuller email
# (HD Ticket.handle_status_change_email). This covers every other move —
# picked up, paused, reopened — so the customer is not left guessing between
# the acknowledgement and the resolution.
#
# It goes out through HD Ticket.send_customer_notice, so it inherits that
# path's gates (automated senders, our own inboxes, agents' own tickets,
# anyone who turned email updates off, the per-ticket loop breaker last and
# RFC 3834 headers) and reaches the requester plus the contacts on the
# customer's card. A WhatsApp ticket is told on WhatsApp instead.
#
# A status set by a reply never notifies: the reply itself just went out, and
# the ticket flips to Replied/Open as part of sending it.

import html

import frappe
from frappe import _
from frappe.utils import cint


def enabled() -> bool:
	"""Settings > Email Notifications > Status updates."""
	return bool(
		cint(frappe.db.get_single_value("HD Settings", "notify_customer_of_status"))
	)


def customer_status_label(status: str | None) -> str:
	"""What the customer calls this status — statuses can read one way to
	agents and another to customers."""
	if not status:
		return ""
	row = frappe.db.get_value(
		"HD Ticket Status",
		status,
		["label_customer", "label_agent", "different_view"],
		as_dict=True,
	)
	if not row:
		return status
	label = (row.label_customer if row.different_view else row.label_agent) or status
	return label[:1].upper() + label[1:]


def status_message(number, subject, label, portal_url, customer_name=None):
	"""(html, text) of the notice that a ticket has moved."""
	e = html.escape
	greeting = _("Hello {0},").format(customer_name) if customer_name else _("Hello,")
	line = _("Your ticket #{0}: {1} is now {2}.").format(number, subject, label)
	follow = _("You can follow it here:")
	html_body = (
		f"<p>{e(greeting)}</p><p>{e(line)}</p>"
		f'<p>{e(follow)} <a href="{e(portal_url)}">{e(portal_url)}</a></p>'
	)
	return html_body, line


def notify_status_change(ticket: str, status: str) -> None:
	"""Background job: tell the customer's team the ticket has moved."""
	if not enabled() or not frappe.db.exists("HD Ticket", ticket):
		return
	t = frappe.get_doc("HD Ticket", ticket)
	# Moved on again before this ran, or landed somewhere that sends its own
	# (fuller) email.
	if t.status != status or t.status_category == "Resolved":
		return

	from helpdesk.api.assignment import _customer_first_name

	label = customer_status_label(t.status)
	body, text = status_message(
		t.name, t.subject, label, t.portal_uri, _customer_first_name(t)
	)
	outcome = t.send_customer_notice(
		"status", _("Ticket #{0} is now {1}").format(t.name, label), body, text
	)
	if outcome == "sent":
		try:
			from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import (
				log_ticket_activity,
			)

			log_ticket_activity(t.name, f"told the customer it is now {label}")
		except Exception:
			pass
