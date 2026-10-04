# Subtasks for HD Addon Task (the Tasks module), mirroring the ticket subtask
# feature. Each subtask carries an assignee, a reviewer, and a review score.
#
# Internal to the team: agents only. Access to a subtask is gated through the
# parent task (helpdesk.api.addon._assert_task_access). Scoring is reserved for
# the subtask's reviewer (or a manager), same rule as the parent task.

import frappe
from frappe import _
from frappe.utils import cint, flt

from helpdesk.api.addon import RESPONSIBILITIES, _assert_task_access
from helpdesk.utils import is_agent, is_agent_manager

SUBTASK_FIELDS = [
	"name",
	"subject",
	"status",
	"responsibility",
	"hours_spent",
	"assigned_to",
	"reviewer",
	"review_status",
	"score",
	"description",
	"due_date",
	"customer_visible",
]
STATUSES = ("To Do", "In Progress", "Done")

# Agents type subjects into a plain Data column, capped server-side so an
# over-long title fails with a message instead of hitting the database limit.
SUBJECT_MAX_LENGTH = 500


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage subtasks"), frappe.PermissionError)


def _resolve_task(subtask: str) -> str:
	task = frappe.db.get_value("HD Task Subtask", subtask, "task")
	if not task:
		frappe.throw(_("Subtask not found"), frappe.DoesNotExistError)
	return task


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
def get_subtasks(task: str) -> list:
	"""Subtasks of a task. Agents see all with assignee/reviewer names; the
	parent's customer sees only customer-visible ones, scrubbed of internal
	review/hours/assignee-email data."""
	_assert_task_access(task)
	agent = is_agent()
	filters: dict = {"task": task}
	if not agent:
		filters["customer_visible"] = 1
	rows = frappe.get_all(
		"HD Task Subtask",
		filters=filters,
		fields=SUBTASK_FIELDS,
		order_by="creation asc",
		ignore_permissions=True,
	)
	people = list(
		{r.assigned_to for r in rows if r.assigned_to}
		| {r.reviewer for r in rows if r.reviewer}
	)
	names = {}
	if people:
		names = {
			a.name: a.agent_name
			for a in frappe.get_all(
				"HD Agent", filters={"name": ["in", people]}, fields=["name", "agent_name"]
			)
		}
	for r in rows:
		r["assigned_to_name"] = names.get(r.assigned_to) or (
			r.assigned_to if agent else _("Support agent") if r.assigned_to else None
		)
		r["reviewer_name"] = names.get(r.reviewer) or r.reviewer
		if not agent:
			# Reviewer, score, hours and the assignee email are internal QA,
			# and responsibility (us/client/joint) is an internal split.
			r["assigned_to"] = None
			r["reviewer"] = None
			r["reviewer_name"] = None
			r["review_status"] = None
			r["score"] = 0
			r["hours_spent"] = 0
			r["responsibility"] = None
	return rows


@frappe.whitelist()
def get_summary(task: str) -> dict:
	"""Progress, hours and review rollup for a task's subtasks. Customers get
	progress over the customer-visible subtasks only (no hours/score)."""
	_assert_task_access(task)
	agent = is_agent()
	filters: dict = {"task": task}
	if not agent:
		filters["customer_visible"] = 1
	rows = frappe.get_all(
		"HD Task Subtask",
		filters=filters,
		fields=["status", "hours_spent", "score", "due_date"],
		ignore_permissions=True,
	)
	total = len(rows)
	done = len([r for r in rows if r.status == "Done"])
	scored = [r.score for r in rows if r.score]
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
		# Hours and scores are internal QA — not exposed on the portal.
		"hours_spent": sum([flt(r.hours_spent) for r in rows]) if agent else 0,
		"avg_score": (round(sum(scored) / len(scored), 1) if scored else 0)
		if agent
		else 0,
		"progress": round((done / total) * 100) if total else 0,
	}


@frappe.whitelist()
def add_subtask(task: str, subject: str, responsibility: str = "Us") -> str:
	"""Create a subtask under a task. Agents only."""
	_assert_agent()
	_assert_task_access(task)
	subject = _clean_subject(subject)
	doc = frappe.get_doc(
		{
			"doctype": "HD Task Subtask",
			"task": task,
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
	reviewer: str | None = None,
	score: int | None = None,
	description: str | None = None,
	due_date: str | None = None,
	customer_visible: int | None = None,
) -> bool:
	"""Update a subtask. Agents only. Scoring is reserved for the subtask's
	reviewer (or a manager)."""
	_assert_agent()
	task = _resolve_task(name)
	_assert_task_access(task)
	doc = frappe.get_doc("HD Task Subtask", name)

	if score is not None:
		# Check against the reviewer as stored, not one set in this request.
		if not (is_agent_manager() or frappe.session.user == doc.reviewer):
			frappe.throw(
				_("Only the reviewer or a manager can score a subtask"),
				frappe.PermissionError,
			)
		doc.score = max(0, min(5, cint(score)))
		# A score IS the review: it signs the subtask off.
		if doc.score:
			doc.review_status = "Reviewed"
	old_status = doc.status
	if subject is not None:
		doc.subject = _clean_subject(subject)
	if status is not None:
		if status not in STATUSES:
			frappe.throw(_("Invalid status"))
		doc.status = status
	if responsibility is not None:
		doc.responsibility = _clean_responsibility(responsibility)
	if hours_spent is not None:
		doc.hours_spent = max(0, flt(hours_spent))
	if assigned_to is not None:
		doc.assigned_to = assigned_to or None
	if reviewer is not None:
		doc.reviewer = reviewer or None
		if not doc.reviewer:
			# Nobody left to review it, so nothing is pending.
			doc.review_status = None
	if description is not None:
		doc.description = description
	if due_date is not None:
		doc.due_date = due_date or None
	if customer_visible is not None:
		doc.customer_visible = 1 if cint(customer_visible) else 0
	# Finishing a subtask that has a reviewer queues it for them, the same
	# rule the parent task follows when it is marked Done.
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
	task = _resolve_task(name)
	_assert_task_access(task)
	frappe.delete_doc("HD Task Subtask", name, ignore_permissions=True)
	return True


# ---------------------------------------------------------------------------
# Review: an agent submits a subtask to the colleague who checks it
# ---------------------------------------------------------------------------


def _notify_subtask_reviewer(doc) -> None:
	"""Tell the reviewer a subtask is waiting on them (in-app + email).
	Best-effort: a notification failure never fails the request, and nobody
	is asked to review their own work."""
	reviewer = doc.get("reviewer")
	if not reviewer or reviewer == frappe.session.user or reviewer == "Guest":
		return
	task = (
		frappe.db.get_value(
			"HD Addon Task", doc.task, ["subject", "project", "addon"], as_dict=True
		)
		or frappe._dict()
	)
	if task.get("project"):
		path = f"/helpdesk/projects/{task.project}"
	elif task.get("addon"):
		path = f"/helpdesk/addons/{task.addon}"
	else:
		path = "/helpdesk/tasks"
	link = frappe.utils.get_url(path)
	try:
		frappe.publish_realtime(
			"helpdesk:subtask_review_requested",
			{
				"subtask": doc.name,
				"subject": doc.subject,
				"task": doc.task,
				"link": link,
			},
			user=reviewer,
		)
	except Exception:
		pass

	sender = frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")
	if not sender:
		return
	try:
		first_name = (
			frappe.db.get_value("HD Agent", reviewer, "agent_name") or reviewer
		).split(" ")[0]
		requester = frappe.utils.get_fullname(frappe.session.user)
		parent = task.get("subject") or doc.task
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
					{_('On task')}: {frappe.utils.escape_html(parent)}</p>
				<p style="margin-top:16px;">
					<a href="{link}" style="background:#2563eb;color:#fff;padding:8px 16px;
					border-radius:6px;text-decoration:none;">{_('Open task')}</a>
				</p>
			""",
			reference_doctype="HD Task Subtask",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Subtask review email failed", message=frappe.get_traceback()
		)


@frappe.whitelist()
def request_review(name: str, reviewer: str | None = None) -> bool:
	"""Submit a subtask to its reviewer: record them, flag it Pending Review
	and notify them. Agents only. Calling it again re-sends the request,
	which is what the "Remind reviewer" button does."""
	_assert_agent()
	task = _resolve_task(name)
	_assert_task_access(task)
	doc = frappe.get_doc("HD Task Subtask", name)
	if reviewer is not None:
		reviewer = (reviewer or "").strip()
		if reviewer and not frappe.db.exists("HD Agent", reviewer):
			frappe.throw(_("{0} is not an agent").format(reviewer))
		doc.reviewer = reviewer or None
	if not doc.reviewer:
		frappe.throw(_("Choose a reviewer first"))
	doc.review_status = "Pending Review"
	doc.save(ignore_permissions=True)
	_notify_subtask_reviewer(doc)
	return True


@frappe.whitelist()
def mark_reviewed(name: str) -> bool:
	"""Sign a subtask off without scoring it — the reviewer named on it, or
	a manager, same rule as scoring."""
	_assert_agent()
	task = _resolve_task(name)
	_assert_task_access(task)
	doc = frappe.get_doc("HD Task Subtask", name)
	if not (is_agent_manager() or frappe.session.user == doc.reviewer):
		frappe.throw(
			_("Only the reviewer or a manager can mark this reviewed"),
			frappe.PermissionError,
		)
	doc.review_status = "Reviewed"
	doc.save(ignore_permissions=True)
	return True
