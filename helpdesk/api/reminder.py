# Reminders API.
#
# Any authenticated user (agent or customer portal) can manage their own
# reminders. The scheduler publishes realtime events for due reminders.

import frappe
from frappe import _
from frappe.utils import now


@frappe.whitelist()
def create_reminder(
	message: str,
	remind_at: str,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> str:
	"""Create a personal reminder. Any authenticated user."""
	if not (message or "").strip():
		frappe.throw(_("Message is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Reminder",
			"message": message.strip(),
			"remind_at": remind_at,
			"reference_doctype": reference_doctype or None,
			"reference_name": reference_name or None,
			"status": "Pending",
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def get_my_reminders() -> list[dict]:
	"""All non-dismissed reminders for the current user, ordered by time."""
	return frappe.get_all(
		"HD Reminder",
		filters={
			"owner": frappe.session.user,
			"status": ["in", ["Pending", "Notified"]],
		},
		fields=[
			"name",
			"message",
			"remind_at",
			"reference_doctype",
			"reference_name",
			"status",
		],
		order_by="remind_at asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def dismiss_reminder(name: str) -> bool:
	"""Dismiss a reminder. Only the owner may dismiss."""
	owner = frappe.db.get_value("HD Reminder", name, "owner")
	if owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.db.set_value("HD Reminder", name, "status", "Dismissed", update_modified=False)
	return True


def send_due_reminders() -> None:
	"""Scheduled hourly. Publishes realtime events for overdue reminders and
	marks them as Notified so they won't fire again."""
	overdue = frappe.get_all(
		"HD Reminder",
		filters={"status": "Pending", "remind_at": ["<=", now()]},
		fields=["name", "owner", "message", "reference_doctype", "reference_name"],
		ignore_permissions=True,
	)
	for r in overdue:
		frappe.publish_realtime(
			"helpdesk:reminder_due",
			{
				"name": r.name,
				"message": r.message,
				"reference_doctype": r.reference_doctype,
				"reference_name": r.reference_name,
			},
			user=r.owner,
		)
		frappe.db.set_value(
			"HD Reminder", r.name, "status", "Notified", update_modified=False
		)
	if overdue:
		frappe.db.commit()
