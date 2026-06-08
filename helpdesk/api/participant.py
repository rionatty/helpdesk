# Ticket participants (CC) API.
#
# Anyone who can READ a ticket (its agents and its customer) may view and manage
# that ticket's participants. Participants are CC'd on agent replies so a
# colleague added by the customer follows the whole conversation.

import frappe
from frappe import _
from frappe.utils import validate_email_address


def _assert_ticket_read(ticket: str) -> None:
	if not frappe.db.exists("HD Ticket", ticket):
		frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
	if not frappe.has_permission("HD Ticket", "read", doc=ticket):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def get_participants(ticket: str) -> list:
	"""Participant rows for a ticket. Allowed for agents and the customer."""
	_assert_ticket_read(ticket)
	return frappe.get_all(
		"HD Ticket Participant",
		filters={"ticket": ticket},
		fields=["name", "email"],
		order_by="creation asc",
	)


@frappe.whitelist()
def add_participant(ticket: str, email: str) -> str | None:
	"""Add a CC participant to a ticket (idempotent)."""
	_assert_ticket_read(ticket)
	email = (email or "").strip().lower()
	validate_email_address(email, throw=True)
	if frappe.db.exists("HD Ticket Participant", {"ticket": ticket, "email": email}):
		return None
	doc = frappe.get_doc(
		{"doctype": "HD Ticket Participant", "ticket": ticket, "email": email}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def remove_participant(name: str) -> bool:
	"""Remove a participant row."""
	doc = frappe.get_doc("HD Ticket Participant", name)
	_assert_ticket_read(doc.ticket)
	frappe.delete_doc("HD Ticket Participant", name, ignore_permissions=True)
	return True
