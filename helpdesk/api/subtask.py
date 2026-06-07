# Copyright (c) 2026, rionatty and contributors
# Subtask + time-tracking API for HD Ticket.
#
# Reads (get_subtasks / get_summary) are allowed for anyone who can READ the
# parent ticket — i.e. agents and the ticket's own customer. Writes require an
# agent. Subtask rows are fetched with frappe.get_all (permission-bypassing) but
# only AFTER the caller's read access to the parent ticket is verified, so a
# customer can see the subtasks of their own ticket without a direct read
# permission on HD Ticket Subtask.

import frappe
from frappe import _

from helpdesk.utils import is_agent


def _assert_ticket_read(ticket: str) -> None:
	if not frappe.db.exists("HD Ticket", ticket):
		frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
	if not frappe.has_permission("HD Ticket", "read", doc=ticket):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage subtasks"), frappe.PermissionError)


@frappe.whitelist()
def get_subtasks(ticket: str) -> list:
	"""Subtasks for a ticket. Allowed for agents and the ticket's customer."""
	_assert_ticket_read(ticket)
	return frappe.get_all(
		"HD Ticket Subtask",
		filters={"ticket": ticket},
		fields=["name", "subject", "status", "hours_spent", "assigned_to", "description"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_summary(ticket: str) -> dict:
	"""Aggregate progress + time for a ticket's subtasks."""
	_assert_ticket_read(ticket)
	rows = frappe.get_all(
		"HD Ticket Subtask",
		filters={"ticket": ticket},
		fields=["status", "hours_spent"],
	)
	total = len(rows)
	done = len([r for r in rows if r.status == "Done"])
	hours_spent = sum([(r.hours_spent or 0) for r in rows])
	estimated_hours = frappe.db.get_value("HD Ticket", ticket, "estimated_hours") or 0
	return {
		"total": total,
		"done": done,
		"in_progress": len([r for r in rows if r.status == "In Progress"]),
		"todo": len([r for r in rows if r.status == "To Do"]),
		"hours_spent": hours_spent,
		"estimated_hours": estimated_hours,
		"progress": round((done / total) * 100) if total else 0,
	}


@frappe.whitelist()
def add_subtask(ticket: str, subject: str) -> str:
	"""Create a subtask under a ticket. Agents only."""
	_assert_agent()
	_assert_ticket_read(ticket)
	subject = (subject or "").strip()
	if not subject:
		frappe.throw(_("Subject is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Ticket Subtask",
			"ticket": ticket,
			"subject": subject,
			"status": "To Do",
			"hours_spent": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_subtask(
	name: str,
	subject: str | None = None,
	status: str | None = None,
	hours_spent: float | None = None,
	assigned_to: str | None = None,
	description: str | None = None,
) -> bool:
	"""Update fields on a subtask. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Ticket Subtask", name)
	_assert_ticket_read(doc.ticket)
	if subject is not None:
		doc.subject = subject.strip()
	if status is not None:
		if status not in ("To Do", "In Progress", "Done"):
			frappe.throw(_("Invalid status"))
		doc.status = status
	if hours_spent is not None:
		doc.hours_spent = max(0, hours_spent)
	if assigned_to is not None:
		doc.assigned_to = assigned_to or None
	if description is not None:
		doc.description = description
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_subtask(name: str) -> bool:
	"""Delete a subtask. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Ticket Subtask", name)
	_assert_ticket_read(doc.ticket)
	frappe.delete_doc("HD Ticket Subtask", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def set_estimate(ticket: str, hours: float) -> bool:
	"""Set the estimated-hours budget on a ticket. Agents only."""
	_assert_agent()
	_assert_ticket_read(ticket)
	frappe.db.set_value("HD Ticket", ticket, "estimated_hours", max(0, hours))
	return True
