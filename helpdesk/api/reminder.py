# Reminders API.
#
# Any authenticated user (agent or customer portal) can manage their own
# reminders. The scheduler publishes realtime events for due reminders and
# optionally sends email.

import frappe
from frappe import _
from frappe.utils import now


@frappe.whitelist()
def create_reminder(
	message: str,
	remind_at: str,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	send_email: bool | int = False,
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
			"send_email": 1 if send_email else 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def get_my_reminders() -> list[dict]:
	"""Non-dismissed, non-performed reminders for the bell popover."""
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
			"send_email",
		],
		order_by="remind_at asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def get_all_my_reminders() -> list[dict]:
	"""All reminders for the current user (all statuses), newest first."""
	return frappe.get_all(
		"HD Reminder",
		filters={"owner": frappe.session.user},
		fields=[
			"name",
			"message",
			"remind_at",
			"reference_doctype",
			"reference_name",
			"status",
			"send_email",
		],
		order_by="remind_at desc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def mark_performed(name: str) -> bool:
	"""Mark a reminder as performed. Only the owner may do this."""
	owner = frappe.db.get_value("HD Reminder", name, "owner")
	if owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.db.set_value("HD Reminder", name, "status", "Performed", update_modified=False)
	return True


@frappe.whitelist()
def update_reminder(name: str, message: str, remind_at: str) -> bool:
	"""Reschedule a reminder and reset it to Pending. Only the owner may do this."""
	owner = frappe.db.get_value("HD Reminder", name, "owner")
	if owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.db.set_value(
		"HD Reminder",
		name,
		{"message": message.strip(), "remind_at": remind_at, "status": "Pending"},
		update_modified=False,
	)
	return True


@frappe.whitelist()
def dismiss_reminder(name: str) -> bool:
	"""Dismiss a reminder. Only the owner may dismiss."""
	owner = frappe.db.get_value("HD Reminder", name, "owner")
	if owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.db.set_value("HD Reminder", name, "status", "Dismissed", update_modified=False)
	return True


def send_due_reminders() -> None:
	"""Scheduled hourly. Publishes realtime events for overdue Pending reminders,
	sends email when requested, then marks them Notified."""
	overdue = frappe.get_all(
		"HD Reminder",
		filters={"status": "Pending", "remind_at": ["<=", now()]},
		fields=[
			"name",
			"owner",
			"message",
			"reference_doctype",
			"reference_name",
			"send_email",
		],
		ignore_permissions=True,
	)
	for r in overdue:
		# Realtime popup in the browser
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
		# Optional email
		if r.send_email:
			try:
				user_email = frappe.db.get_value("User", r.owner, "email") or r.owner
				user_name = frappe.db.get_value("User", r.owner, "full_name") or r.owner
				ref_line = (
					f"<p><strong>Reference:</strong> {r.reference_doctype} — {r.reference_name}</p>"
					if r.reference_name
					else ""
				)
				frappe.sendmail(
					recipients=[user_email],
					subject=_("Reminder: {0}").format(r.message[:80]),
					message=f"""
						<p>Hi {user_name},</p>
						<p>This is a reminder you set in the support portal:</p>
						<blockquote style="border-left:3px solid #ccc;margin:8px 0;padding:4px 12px">
							{r.message}
						</blockquote>
						{ref_line}
						<p style="color:#888;font-size:12px">
							You can view and manage all your reminders from the support portal.
						</p>
					""",
					now=True,
				)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "HD Reminder email failed")

		frappe.db.set_value(
			"HD Reminder", r.name, "status", "Notified", update_modified=False
		)
	if overdue:
		frappe.db.commit()
