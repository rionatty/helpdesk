# Subtasks for HD Addon Task (the Tasks module), mirroring the ticket subtask
# feature. Each subtask carries an assignee, a reviewer, and a review score.
#
# Internal to the team: agents only. Access to a subtask is gated through the
# parent task (helpdesk.api.addon._assert_task_access). Scoring is reserved for
# the subtask's reviewer (or a manager), same rule as the parent task.

import frappe
from frappe import _
from frappe.utils import cint, flt

from helpdesk.api.addon import _assert_task_access
from helpdesk.utils import is_agent, is_agent_manager

SUBTASK_FIELDS = [
	"name",
	"subject",
	"status",
	"hours_spent",
	"assigned_to",
	"reviewer",
	"score",
	"description",
	"due_date",
	"customer_visible",
]
STATUSES = ("To Do", "In Progress", "Done")


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage subtasks"), frappe.PermissionError)


def _resolve_task(subtask: str) -> str:
	task = frappe.db.get_value("HD Task Subtask", subtask, "task")
	if not task:
		frappe.throw(_("Subtask not found"), frappe.DoesNotExistError)
	return task


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
			# Reviewer, score, hours and the assignee email are internal QA.
			r["assigned_to"] = None
			r["reviewer"] = None
			r["reviewer_name"] = None
			r["score"] = 0
			r["hours_spent"] = 0
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
def add_subtask(task: str, subject: str) -> str:
	"""Create a subtask under a task. Agents only."""
	_assert_agent()
	_assert_task_access(task)
	subject = (subject or "").strip()
	if not subject:
		frappe.throw(_("Subject is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Task Subtask",
			"task": task,
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
	if subject is not None:
		doc.subject = subject.strip()
	if status is not None:
		if status not in STATUSES:
			frappe.throw(_("Invalid status"))
		doc.status = status
	if hours_spent is not None:
		doc.hours_spent = max(0, flt(hours_spent))
	if assigned_to is not None:
		doc.assigned_to = assigned_to or None
	if reviewer is not None:
		doc.reviewer = reviewer or None
	if description is not None:
		doc.description = description
	if due_date is not None:
		doc.due_date = due_date or None
	if customer_visible is not None:
		doc.customer_visible = 1 if cint(customer_visible) else 0
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_subtask(name: str) -> bool:
	"""Delete a subtask. Agents only."""
	_assert_agent()
	task = _resolve_task(name)
	_assert_task_access(task)
	frappe.delete_doc("HD Task Subtask", name, ignore_permissions=True)
	return True
