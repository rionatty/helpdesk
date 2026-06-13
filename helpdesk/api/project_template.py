# Copyright (c) 2026, rionatty and contributors
# Project template API: list templates, apply one to a project (creates
# milestones + tasks), and snapshot an existing project as a template.
# All endpoints are agent-only.

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from helpdesk.utils import is_agent

# Fields we accept from the editor for each child row — anything else is ignored.
MILESTONE_ROW_FIELDS = (
	"title",
	"sequence",
	"due_after_days",
	"customer_visible",
	"description",
)
TASK_ROW_FIELDS = (
	"subject",
	"milestone_title",
	"status",
	"priority",
	"assigned_to",
	"is_internal",
	"description",
)


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage project templates"), frappe.PermissionError)


def _assert_project(project: str) -> None:
	if not frappe.db.exists("HD Project", project):
		frappe.throw(_("Project not found"), frappe.DoesNotExistError)


@frappe.whitelist()
def get_templates() -> list:
	"""Templates with milestone/task counts, newest first."""
	_assert_agent()
	templates = frappe.get_all(
		"HD Project Template",
		fields=["name", "template_name", "description", "modified"],
		order_by="modified desc",
	)
	for t in templates:
		t["milestone_count"] = frappe.db.count(
			"HD Project Template Milestone", {"parent": t.name}
		)
		t["task_count"] = frappe.db.count(
			"HD Project Template Task", {"parent": t.name}
		)
	return templates


@frappe.whitelist()
def get_template(name: str) -> dict:
	"""A single template with its milestone and task rows, for the editor."""
	_assert_agent()
	if not frappe.db.exists("HD Project Template", name):
		frappe.throw(_("Template not found"), frappe.DoesNotExistError)
	doc = frappe.get_doc("HD Project Template", name)
	return {
		"name": doc.name,
		"template_name": doc.template_name,
		"description": doc.description,
		"milestones": [
			{
				"title": m.title,
				"sequence": m.sequence or 0,
				"due_after_days": m.due_after_days or 0,
				"customer_visible": cint(m.customer_visible),
				"description": m.description,
			}
			for m in sorted(doc.milestones or [], key=lambda r: r.sequence or 0)
		],
		"tasks": [
			{
				"subject": t.subject,
				"milestone_title": t.milestone_title or "",
				"status": t.status or "To Do",
				"priority": t.priority or "Medium",
				"assigned_to": t.assigned_to,
				"is_internal": cint(t.is_internal),
				"description": t.description,
			}
			for t in (doc.tasks or [])
		],
	}


@frappe.whitelist()
def create_template(template_name: str, description: str | None = None) -> str:
	"""Create an empty template. Agents only."""
	_assert_agent()
	template_name = (template_name or "").strip()
	if not template_name:
		frappe.throw(_("Template name is required"))
	if frappe.db.exists("HD Project Template", template_name):
		frappe.throw(_("A template named '{0}' already exists").format(template_name))
	doc = frappe.get_doc(
		{
			"doctype": "HD Project Template",
			"template_name": template_name,
			"description": description,
		}
	).insert(ignore_permissions=True)
	return doc.name


def _clean_milestone_rows(rows: list) -> list:
	cleaned = []
	for r in rows or []:
		title = (r.get("title") or "").strip()
		if not title:
			continue
		cleaned.append(
			{
				"title": title,
				"sequence": cint(r.get("sequence")),
				"due_after_days": max(0, cint(r.get("due_after_days"))),
				"customer_visible": cint(r.get("customer_visible")),
				"description": r.get("description"),
			}
		)
	return cleaned


def _clean_task_rows(rows: list) -> list:
	cleaned = []
	for r in rows or []:
		subject = (r.get("subject") or "").strip()
		if not subject:
			continue
		assignee = r.get("assigned_to") or None
		if assignee and not frappe.db.exists("HD Agent", assignee):
			assignee = None
		cleaned.append(
			{
				"subject": subject,
				"milestone_title": (r.get("milestone_title") or "").strip(),
				"status": r.get("status") or "To Do",
				"priority": r.get("priority") or "Medium",
				"assigned_to": assignee,
				"is_internal": cint(r.get("is_internal")),
				"description": r.get("description"),
			}
		)
	return cleaned


@frappe.whitelist()
def update_template(
	name: str,
	template_name: str | None = None,
	description: str | None = None,
	milestones=None,
	tasks=None,
) -> str:
	"""Rewrite a template's name, description and child rows. Agents only.
	`milestones` and `tasks` are JSON arrays (full replacement)."""
	_assert_agent()
	if not frappe.db.exists("HD Project Template", name):
		frappe.throw(_("Template not found"), frappe.DoesNotExistError)

	new_name = (template_name or "").strip()
	if new_name and new_name != name:
		if frappe.db.exists("HD Project Template", new_name):
			frappe.throw(
				_("A template named '{0}' already exists").format(new_name)
			)
		frappe.rename_doc("HD Project Template", name, new_name, force=True)
		name = new_name

	doc = frappe.get_doc("HD Project Template", name)
	if description is not None:
		doc.description = description
	if milestones is not None:
		doc.set("milestones", [])
		for m in _clean_milestone_rows(frappe.parse_json(milestones)):
			doc.append("milestones", m)
	if tasks is not None:
		doc.set("tasks", [])
		for t in _clean_task_rows(frappe.parse_json(tasks)):
			doc.append("tasks", t)
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def delete_template(name: str) -> bool:
	"""Delete a template and its rows (child rows cascade). Agents only."""
	_assert_agent()
	if not frappe.db.exists("HD Project Template", name):
		return True
	frappe.delete_doc("HD Project Template", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def apply_template(project: str, template: str) -> dict:
	"""Instantiate a template's milestones + tasks into a project.

	Milestone due dates are offset from the project's start date (or today) by
	each row's due_after_days. Re-applying is safe and idempotent: a milestone
	is reused when one with the same title already exists, and a task is skipped
	when one with the same subject + milestone already exists on the project.
	"""
	_assert_agent()
	_assert_project(project)
	tpl = frappe.get_doc("HD Project Template", template)

	# Anchor milestone due dates on the project's start date when it has one,
	# so "due after N days" is measured from the project start; else from today.
	base = frappe.db.get_value("HD Project", project, "start_date")
	today = getdate(base) if base else getdate(nowdate())
	milestone_map: dict = {}
	milestones_created = 0
	tasks_created = 0

	for row in sorted(tpl.milestones or [], key=lambda r: r.sequence or 0):
		title = (row.title or "").strip()
		if not title:
			continue
		existing = frappe.db.get_value(
			"HD Milestone", {"project": project, "title": title}, "name"
		)
		if existing:
			milestone_map[title] = existing
			continue
		doc = frappe.get_doc(
			{
				"doctype": "HD Milestone",
				"title": title,
				"project": project,
				"status": "Upcoming",
				"sequence": row.sequence or 0,
				"due_date": add_days(today, row.due_after_days or 0),
				"customer_visible": row.customer_visible,
				"description": row.description,
			}
		).insert(ignore_permissions=True)
		milestone_map[title] = doc.name
		milestones_created += 1

	for row in tpl.tasks or []:
		subject = (row.subject or "").strip()
		if not subject:
			continue
		milestone_title = (row.milestone_title or "").strip()
		milestone_name = milestone_map.get(milestone_title)
		# Idempotent: skip if an identical task already exists on this project,
		# so re-applying never duplicates tasks (which would also regress a
		# manually-completed milestone via the task→milestone sync).
		dup_filters = {"project": project, "subject": subject}
		dup_filters["milestone"] = milestone_name or ["is", "not set"]
		if frappe.db.exists("HD Addon Task", dup_filters):
			continue
		assignee = row.assigned_to
		if assignee and not frappe.db.exists("HD Agent", assignee):
			assignee = None
		doc = frappe.get_doc(
			{
				"doctype": "HD Addon Task",
				"subject": subject,
				"project": project,
				"milestone": milestone_name,
				"status": row.status or "To Do",
				"priority": row.priority or "Medium",
				"assigned_to": assignee,
				"is_internal": row.is_internal,
				"description": row.description,
			}
		).insert(ignore_permissions=True)
		tasks_created += 1

	return {
		"milestones_created": milestones_created,
		"milestones_reused": len(milestone_map) - milestones_created,
		"tasks_created": tasks_created,
	}


@frappe.whitelist()
def save_as_template(project: str, template_name: str) -> str:
	"""Snapshot a project's milestones + tasks into a new template.

	due_after_days is derived from each milestone's due date relative to the
	project start date (falling back to the earliest milestone due date, then
	today), so applying the template later reproduces the same spacing.
	"""
	_assert_agent()
	_assert_project(project)
	template_name = (template_name or "").strip()
	if not template_name:
		frappe.throw(_("Template name is required"))
	if frappe.db.exists("HD Project Template", template_name):
		frappe.throw(_("A template named '{0}' already exists").format(template_name))

	milestones = frappe.get_all(
		"HD Milestone",
		filters={"project": project},
		fields=[
			"name",
			"title",
			"sequence",
			"due_date",
			"customer_visible",
			"description",
		],
		order_by="sequence asc, creation asc",
	)
	tasks = frappe.get_all(
		"HD Addon Task",
		filters={"project": project},
		fields=[
			"subject",
			"milestone",
			"status",
			"priority",
			"assigned_to",
			"is_internal",
			"description",
		],
		order_by="creation asc",
	)
	if not milestones and not tasks:
		frappe.throw(_("This project has no milestones or tasks to save"))

	base_date = frappe.db.get_value("HD Project", project, "start_date")
	if not base_date:
		due_dates = [m.due_date for m in milestones if m.due_date]
		base_date = min(due_dates) if due_dates else nowdate()
	base_date = getdate(base_date)

	milestone_title_by_name = {m.name: m.title for m in milestones}

	tpl = frappe.new_doc("HD Project Template")
	tpl.template_name = template_name
	for m in milestones:
		offset = (getdate(m.due_date) - base_date).days if m.due_date else 0
		tpl.append(
			"milestones",
			{
				"title": m.title,
				"sequence": m.sequence or 0,
				"due_after_days": max(0, offset),
				"customer_visible": m.customer_visible,
				"description": m.description,
			},
		)
	for t in tasks:
		tpl.append(
			"tasks",
			{
				"subject": t.subject,
				"milestone_title": milestone_title_by_name.get(t.milestone) or "",
				"status": t.status or "To Do",
				"priority": t.priority or "Medium",
				"assigned_to": t.assigned_to,
				"is_internal": t.is_internal,
				"description": t.description,
			},
		)
	tpl.insert(ignore_permissions=True)
	return tpl.name
