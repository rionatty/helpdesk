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

from helpdesk.utils import is_agent, is_agent_manager

# Agents type subjects into a plain Data column, capped server-side so an
# over-long title fails with a message instead of hitting the database limit.
SUBJECT_MAX_LENGTH = 500

# Who does the work: us (the implementor), the client, or both. Internal to the
# team — unrelated to what the customer can see on the portal.
RESPONSIBILITIES = ("Us", "Client", "Joint")

SUBTASK_FIELDS = [
	"name",
	"subject",
	"status",
	"responsibility",
	"hours_spent",
	"assigned_to",
	"description",
	"due_date",
	"reviewer",
	"review_status",
]


def _assert_ticket_read(ticket: str) -> None:
	if not frappe.db.exists("HD Ticket", ticket):
		frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
	if not frappe.has_permission("HD Ticket", "read", doc=ticket):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage subtasks"), frappe.PermissionError)


def _clean_subject(subject: str | None) -> str:
	"""Trim a subject, and refuse one that is empty or longer than the column.

	The column is varchar(500), so a longer subject would be rejected by the
	database anyway -- this turns that into a message the caller can read.
	"""
	subject = (subject or "").strip()
	if not subject:
		frappe.throw(_("Subject is required"))
	if len(subject) > SUBJECT_MAX_LENGTH:
		frappe.throw(
			_("A subject can be at most {0} characters (this one is {1})").format(
				SUBJECT_MAX_LENGTH, len(subject)
			)
		)
	return subject


def _clean_responsibility(responsibility: str | None) -> str:
	"""Who does the work. Falls back to "Us"; refuses anything else."""
	responsibility = (responsibility or "Us").strip()
	if responsibility not in RESPONSIBILITIES:
		frappe.throw(_("Invalid responsibility"))
	return responsibility


@frappe.whitelist()
def get_subtasks(ticket: str) -> list:
	"""Subtasks for a ticket. Allowed for agents and the ticket's customer.

	Includes assigned_to_name (the agent's display name) so the customer view
	can show who's handling a subtask without needing HD Agent read access.
	"""
	_assert_ticket_read(ticket)
	rows = frappe.get_all(
		"HD Ticket Subtask",
		filters={"ticket": ticket},
		fields=SUBTASK_FIELDS,
		order_by="creation asc",
	)
	if rows:
		names = {r.get("assigned_to") for r in rows if r.get("assigned_to")}
		names |= {r.get("reviewer") for r in rows if r.get("reviewer")}
		name_map = {}
		if names:
			name_map = {
				a.name: a.agent_name
				for a in frappe.get_all(
					"HD Agent",
					filters={"name": ["in", list(names)]},
					fields=["name", "agent_name"],
				)
			}
		agent = is_agent()
		for r in rows:
			assignee = r.get("assigned_to")
			# Assignees are agents; the portal gets a display name, never an email.
			r["assigned_to_name"] = name_map.get(assignee) or (
				assignee if agent else (_("Support agent") if assignee else None)
			)
			reviewer = r.get("reviewer")
			r["reviewer_name"] = (
				(name_map.get(reviewer) or reviewer) if agent and reviewer else None
			)
			if not agent:
				# Responsibility (us/client/joint) is an internal split, and so
				# is who reviews our work — neither belongs on the portal.
				r["assigned_to"] = None
				r["responsibility"] = None
				r["reviewer"] = None
				r["review_status"] = None
	return rows


def _ticket_level_hours(ticket: str) -> float:
	"""Time logged on the ticket itself rather than on one of its subtasks
	(helpdesk/api/contracts.py). Subtask time is already in hours_spent."""
	try:
		return sum(
			frappe.utils.flt(h)
			for h in frappe.get_all(
				"HD Time Log",
				filters={"ticket": ticket, "subtask": ["is", "not set"]},
				pluck="hours",
			)
		)
	except Exception:
		return 0  # table may not exist yet (pre-migrate)


@frappe.whitelist()
def get_summary(ticket: str) -> dict:
	"""Aggregate progress + time for a ticket's subtasks."""
	_assert_ticket_read(ticket)
	rows = frappe.get_all(
		"HD Ticket Subtask",
		filters={"ticket": ticket},
		fields=["status", "hours_spent", "due_date", "review_status"],
	)
	total = len(rows)
	done = len([r for r in rows if r.status == "Done"])
	hours_spent = sum([(r.hours_spent or 0) for r in rows]) + _ticket_level_hours(ticket)
	estimated_hours = frappe.db.get_value("HD Ticket", ticket, "estimated_hours") or 0
	today = frappe.utils.getdate()
	overdue = len(
		[
			r
			for r in rows
			if r.status != "Done"
			and r.due_date
			and frappe.utils.getdate(r.due_date) < today
		]
	)
	return {
		"total": total,
		"done": done,
		"in_progress": len([r for r in rows if r.status == "In Progress"]),
		"todo": len([r for r in rows if r.status == "To Do"]),
		"overdue": overdue,
		"hours_spent": hours_spent,
		"estimated_hours": estimated_hours,
		"progress": round((done / total) * 100) if total else 0,
		"pending_review": len(
			[r for r in rows if r.get("review_status") == "Pending Review"]
		)
		if is_agent()
		else 0,
	}


@frappe.whitelist()
def add_subtask(ticket: str, subject: str, responsibility: str = "Us") -> str:
	"""Create a subtask under a ticket. Agents only."""
	_assert_agent()
	_assert_ticket_read(ticket)
	subject = _clean_subject(subject)
	doc = frappe.get_doc(
		{
			"doctype": "HD Ticket Subtask",
			"ticket": ticket,
			"subject": subject,
			"status": "To Do",
			"responsibility": _clean_responsibility(responsibility),
			"hours_spent": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_subtask(
	name: str,
	subject: str | None = None,
	status: str | None = None,
	responsibility: str | None = None,
	hours_spent: float | None = None,
	assigned_to: str | None = None,
	description: str | None = None,
	due_date: str | None = None,
	reviewer: str | None = None,
) -> bool:
	"""Update fields on a subtask. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Ticket Subtask", name)
	_assert_ticket_read(doc.ticket)
	old_status = doc.status
	if subject is not None:
		doc.subject = _clean_subject(subject)
	if status is not None:
		if status not in ("To Do", "In Progress", "Done"):
			frappe.throw(_("Invalid status"))
		doc.status = status
	if responsibility is not None:
		doc.responsibility = _clean_responsibility(responsibility)
	if hours_spent is not None:
		doc.hours_spent = max(0, hours_spent)
	if assigned_to is not None:
		doc.assigned_to = assigned_to or None
	if description is not None:
		doc.description = description
	if due_date is not None:
		doc.due_date = due_date or None
	if reviewer is not None:
		doc.reviewer = _clean_reviewer(reviewer)
		if not doc.reviewer:
			# No reviewer, nothing to review.
			doc.review_status = None
	# Finishing a subtask that has a reviewer queues it for their review, the
	# same way an add-on task does when it is marked Done.
	queue_review = bool(
		doc.status == "Done"
		and old_status != "Done"
		and doc.reviewer
		and doc.review_status != "Reviewed"
	)
	if queue_review:
		doc.review_status = "Pending Review"
	doc.save(ignore_permissions=True)
	if queue_review:
		_notify_subtask_reviewer(doc)
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


# ---------------------------------------------------------------------------
# Review: an agent asks a colleague to check a subtask before it ships
# ---------------------------------------------------------------------------


def _clean_reviewer(reviewer: str | None) -> str | None:
	"""An empty value clears the reviewer; anything else must be an agent."""
	reviewer = (reviewer or "").strip()
	if not reviewer:
		return None
	if not frappe.db.exists("HD Agent", reviewer):
		frappe.throw(_("{0} is not an agent").format(reviewer))
	return reviewer


def _outgoing_sender() -> str | None:
	"""Best available outgoing sender — frappe.sendmail needs one and it isn't
	always flagged Default Outgoing."""
	return frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")


def _notify_subtask_reviewer(doc) -> None:
	"""Tell the reviewer a subtask is waiting on them (in-app + email).
	Best-effort: a notification failure never fails the request, and nobody
	is asked to review their own work."""
	reviewer = doc.get("reviewer")
	if not reviewer or reviewer == frappe.session.user or reviewer == "Guest":
		return
	link = frappe.utils.get_url(f"/helpdesk/tickets/{doc.ticket}")
	try:
		frappe.publish_realtime(
			"helpdesk:subtask_review_requested",
			{
				"subtask": doc.name,
				"subject": doc.subject,
				"ticket": doc.ticket,
				"link": link,
			},
			user=reviewer,
		)
	except Exception:
		pass

	sender = _outgoing_sender()
	if not sender:
		return
	try:
		first_name = (
			frappe.db.get_value("HD Agent", reviewer, "agent_name") or reviewer
		).split(" ")[0]
		requester = frappe.utils.get_fullname(frappe.session.user)
		frappe.sendmail(
			recipients=[reviewer],
			sender=sender,
			subject=_("Review requested: {0}").format(doc.subject),
			message=f"""
				<p>{_('Hi')} {frappe.utils.escape_html(first_name)},</p>
				<p>{frappe.utils.escape_html(requester)}
					{_('asked you to review a subtask')}:</p>
				<p style="font-size:15px;font-weight:600;margin:12px 0;">
					{frappe.utils.escape_html(doc.subject)}</p>
				<p style="color:#6b7280;margin:0 0 12px;">
					{_('On ticket')} #{frappe.utils.escape_html(doc.ticket)}</p>
				<p style="margin-top:16px;">
					<a href="{link}" style="background:#2563eb;color:#fff;padding:8px 16px;
					border-radius:6px;text-decoration:none;">{_('Open ticket')}</a>
				</p>
			""",
			reference_doctype="HD Ticket Subtask",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Subtask review email failed", message=frappe.get_traceback()
		)


def _notify_review_done(doc) -> None:
	"""Tell whoever did the work that the review came back. In-app only —
	they are already working in the ticket; an email would be noise."""
	target = doc.get("assigned_to") or doc.get("owner")
	if not target or target == frappe.session.user or target == "Guest":
		return
	try:
		frappe.publish_realtime(
			"helpdesk:subtask_reviewed",
			{
				"subtask": doc.name,
				"subject": doc.subject,
				"ticket": doc.ticket,
				"reviewer": frappe.utils.get_fullname(frappe.session.user),
			},
			user=target,
		)
	except Exception:
		pass


@frappe.whitelist()
def request_review(name: str, reviewer: str | None = None) -> bool:
	"""Ask an agent to review a subtask: record the reviewer, flag it Pending
	Review and notify them. Agents only. Calling it again re-sends the
	request, which is what the "Remind reviewer" button does."""
	_assert_agent()
	doc = frappe.get_doc("HD Ticket Subtask", name)
	_assert_ticket_read(doc.ticket)
	if reviewer is not None:
		doc.reviewer = _clean_reviewer(reviewer)
	if not doc.reviewer:
		frappe.throw(_("Choose a reviewer first"))
	doc.review_status = "Pending Review"
	doc.save(ignore_permissions=True)
	_notify_subtask_reviewer(doc)
	return True


@frappe.whitelist()
def mark_reviewed(name: str) -> bool:
	"""Mark a subtask reviewed. Only the agent who was asked to review it,
	or a manager, can sign it off."""
	_assert_agent()
	doc = frappe.get_doc("HD Ticket Subtask", name)
	_assert_ticket_read(doc.ticket)
	if not (is_agent_manager() or frappe.session.user == doc.reviewer):
		frappe.throw(
			_("Only the reviewer or a manager can mark this reviewed"),
			frappe.PermissionError,
		)
	doc.review_status = "Reviewed"
	doc.save(ignore_permissions=True)
	_notify_review_done(doc)
	return True
