# Add-ons API.
#
# Agents manage add-ons (deployed apps/modules per customer). Customers view
# their own company's add-ons (read-only). Access is checked explicitly, then
# queries run with ignore_permissions.

import frappe
from frappe import _
from frappe.utils import cint

from helpdesk.utils import get_customer, is_agent

ADDON_FIELDS = [
	"name",
	"addon_name",
	"customer",
	"status",
	"version",
	"activated_on",
	"renewal_date",
	"notes",
	"modified",
]

WRITABLE = {
	"addon_name",
	"customer",
	"status",
	"version",
	"activated_on",
	"renewal_date",
	"notes",
}


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage add-ons"), frappe.PermissionError)


@frappe.whitelist()
def get_addons(customer: str | None = None) -> list:
	"""List add-ons. Agents see all (optionally by customer); customers see
	only their company's add-ons."""
	filters: dict = {}
	if customer:
		filters["customer"] = customer
	if not is_agent():
		companies = get_customer(frappe.session.user)
		if not companies:
			return []
		filters["customer"] = ["in", companies]
	return frappe.get_all(
		"HD Addon",
		filters=filters,
		fields=ADDON_FIELDS,
		order_by="modified desc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def create_addon(
	addon_name: str,
	customer: str,
	status: str = "Active",
	version: str | None = None,
	activated_on: str | None = None,
	renewal_date: str | None = None,
	notes: str | None = None,
) -> str:
	"""Create an add-on. Agents only."""
	_assert_agent()
	if not (addon_name or "").strip():
		frappe.throw(_("Add-on name is required"))
	if not customer:
		frappe.throw(_("Customer is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Addon",
			"addon_name": addon_name.strip(),
			"customer": customer,
			"status": status or "Active",
			"version": version,
			"activated_on": activated_on,
			"renewal_date": renewal_date,
			"notes": notes,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_addon(name: str, **fields) -> bool:
	"""Update writable add-on fields. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Addon", name)
	for key, value in fields.items():
		if key in WRITABLE:
			doc.set(key, value)
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_addon(name: str) -> bool:
	"""Delete an add-on and its features/tasks. Agents only."""
	_assert_agent()
	frappe.db.delete("HD Addon Feature", {"addon": name})
	frappe.db.delete("HD Addon Task", {"addon": name})
	frappe.delete_doc("HD Addon", name, ignore_permissions=True)
	return True


# ---------------------------------------------------------------------------
# Add-on detail: features, tasks, linked tickets, dashboard
# ---------------------------------------------------------------------------

FEATURE_FIELDS = [
	"name",
	"feature_title",
	"status",
	"project",
	"milestone",
	"target_date",
	"released_on",
	"description",
]
FEATURE_WRITABLE = {
	"feature_title",
	"status",
	"project",
	"milestone",
	"target_date",
	"released_on",
	"description",
}
TASK_FIELDS = [
	"name",
	"subject",
	"status",
	"priority",
	"assigned_to",
	"milestone",
	"feature",
	"ticket",
	"is_internal",
	"start_date",
	"end_date",
	"description",
]
TASK_WRITABLE = {
	"subject",
	"status",
	"priority",
	"assigned_to",
	"milestone",
	"feature",
	"ticket",
	"is_internal",
	"start_date",
	"end_date",
	"description",
}


def _assert_addon_access(addon: str) -> frappe._dict:
	"""Agents always; customers only for their own company's add-ons."""
	row = frappe.db.get_value("HD Addon", addon, ["name", "customer"], as_dict=True)
	if not row:
		frappe.throw(_("Add-on not found"), frappe.DoesNotExistError)
	if is_agent():
		return row
	if row.customer and row.customer in get_customer(frappe.session.user):
		return row
	frappe.throw(_("Not permitted"), frappe.PermissionError)


def _get_features(addon: str) -> list:
	# Degrade gracefully if the table isn't migrated yet.
	try:
		return frappe.get_all(
			"HD Addon Feature",
			filters={"addon": addon},
			fields=FEATURE_FIELDS,
			order_by="creation asc",
			ignore_permissions=True,
		)
	except Exception:
		return []


def _get_tasks(addon: str | None = None, project: str | None = None) -> list:
	"""Tasks for an add-on OR a project, with assignee names + comment counts.
	Portal users don't get internal tasks, nor agent emails."""
	filters: dict = {"addon": addon} if addon else {"project": project}
	agent = is_agent()
	if not agent:
		filters["is_internal"] = 0
	try:
		rows = frappe.get_all(
			"HD Addon Task",
			filters=filters,
			fields=TASK_FIELDS,
			order_by="modified desc",
			ignore_permissions=True,
		)
	except Exception:
		return []
	users = list({r.assigned_to for r in rows if r.assigned_to})
	names = {}
	if users:
		names = {
			a.name: a.agent_name
			for a in frappe.get_all(
				"HD Agent", filters={"name": ["in", users]}, fields=["name", "agent_name"]
			)
		}
	counts = {}
	if rows:
		try:
			counts = {
				c.task: c.n
				for c in frappe.get_all(
					"HD Task Comment",
					filters={"task": ["in", [r.name for r in rows]]},
					fields=["task", "count(name) as n"],
					group_by="task",
					ignore_permissions=True,
				)
			}
		except Exception:
			counts = {}
	for r in rows:
		r["assigned_to_name"] = names.get(r.assigned_to) or r.assigned_to
		r["comment_count"] = counts.get(r.name, 0)
		if not agent:
			# assigned_to is an email; portal gets the display name only.
			r["assigned_to"] = None
	return rows


def _assert_parent_access(
	addon: str | None = None, project: str | None = None
) -> None:
	"""Access to a task's parent (add-on or project): agents, or its customer."""
	if addon:
		_assert_addon_access(addon)
		return
	if project:
		row = frappe.db.get_value(
			"HD Project", project, ["customer", "project_type"], as_dict=True
		)
		if not row:
			frappe.throw(_("Project not found"), frappe.DoesNotExistError)
		if is_agent():
			return
		if (row.project_type or "Customer") == "Internal":
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		if row.customer and row.customer in get_customer(frappe.session.user):
			return
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.throw(_("A parent add-on or project is required"))


def _assert_task_access(task: str) -> frappe._dict:
	row = frappe.db.get_value(
		"HD Addon Task", task, ["addon", "project"], as_dict=True
	)
	if not row:
		frappe.throw(_("Task not found"), frappe.DoesNotExistError)
	_assert_parent_access(addon=row.addon, project=row.project)
	return row


def _linked_tickets(addon: str) -> list:
	try:
		return frappe.get_all(
			"HD Ticket",
			filters={"addon": addon},
			fields=["name", "subject", "status"],
			order_by="modified desc",
			ignore_permissions=True,
		)
	except Exception:
		return []


def _count_by(rows: list, field: str) -> dict:
	out: dict = {}
	for r in rows:
		key = r.get(field) or "—"
		out[key] = out.get(key, 0) + 1
	return out


@frappe.whitelist()
def get_addon(name: str) -> dict:
	"""A single add-on with features, tasks (agents only), linked tickets and a
	small dashboard."""
	_assert_addon_access(name)
	doc = frappe.get_doc("HD Addon", name).as_dict()
	features = _get_features(name)
	tasks = _get_tasks(addon=name)
	tickets = _linked_tickets(name)
	doc["features"] = features
	doc["tasks"] = tasks
	doc["tickets"] = tickets
	doc["dashboard"] = {
		"features_total": len(features),
		"features_by_status": _count_by(features, "status"),
		"tasks_total": len(tasks),
		"tasks_by_status": _count_by(tasks, "status"),
		"tickets_total": len(tickets),
	}
	return doc


@frappe.whitelist()
def get_features(addon: str) -> list:
	"""Features for an add-on. Agents and the add-on's customer."""
	_assert_addon_access(addon)
	return _get_features(addon)


@frappe.whitelist()
def add_feature(
	addon: str,
	feature_title: str,
	status: str = "Planned",
	project: str | None = None,
	target_date: str | None = None,
	released_on: str | None = None,
	description: str | None = None,
) -> str:
	"""Add a feature to an add-on. Agents only."""
	_assert_agent()
	_assert_addon_access(addon)
	if not (feature_title or "").strip():
		frappe.throw(_("Feature title is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Addon Feature",
			"addon": addon,
			"feature_title": feature_title.strip(),
			"status": status or "Planned",
			"project": project or None,
			"target_date": target_date,
			"released_on": released_on,
			"description": description,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_feature(name: str, **fields) -> bool:
	"""Update a feature (incl. tagging it to a project). Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Addon Feature", name)
	for key, value in fields.items():
		if key in FEATURE_WRITABLE:
			doc.set(key, value or None if key == "project" else value)
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_feature(name: str) -> bool:
	"""Delete a feature. Agents only."""
	_assert_agent()
	frappe.delete_doc("HD Addon Feature", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_tasks(addon: str | None = None, project: str | None = None) -> list:
	"""Tasks for an add-on or project. Agents and the parent's customer (view)."""
	_assert_parent_access(addon=addon, project=project)
	return _get_tasks(addon=addon, project=project)


@frappe.whitelist()
def add_task(
	subject: str,
	addon: str | None = None,
	project: str | None = None,
	milestone: str | None = None,
	feature: str | None = None,
	ticket: str | None = None,
	status: str = "To Do",
	priority: str = "Medium",
	assigned_to: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	description: str | None = None,
	is_internal: int = 0,
) -> str:
	"""Add a task to an add-on or project. Agents only."""
	_assert_agent()
	_assert_parent_access(addon=addon, project=project)
	if not (subject or "").strip():
		frappe.throw(_("Task title is required"))
	if milestone and project:
		if frappe.db.get_value("HD Milestone", milestone, "project") != project:
			frappe.throw(_("Milestone belongs to a different project"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Addon Task",
			"addon": addon or None,
			"project": project or None,
			"milestone": milestone or None,
			"feature": feature or None,
			"ticket": ticket or None,
			"subject": subject.strip(),
			"status": status or "To Do",
			"priority": priority or "Medium",
			"assigned_to": assigned_to or None,
			"start_date": start_date,
			"end_date": end_date,
			"description": description,
			"is_internal": 1 if cint(is_internal) else 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_task(name: str, **fields) -> bool:
	"""Update a task. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Addon Task", name)
	for key, value in fields.items():
		if key in TASK_WRITABLE:
			doc.set(key, value)
	if doc.milestone and doc.project:
		if frappe.db.get_value("HD Milestone", doc.milestone, "project") != doc.project:
			frappe.throw(_("Milestone belongs to a different project"))
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_task(name: str) -> bool:
	"""Delete a task and its comments. Agents only."""
	_assert_agent()
	frappe.db.delete("HD Task Comment", {"task": name})
	frappe.delete_doc("HD Addon Task", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_task_comments(task: str) -> list:
	"""Comments on a task. Agents and the parent's customer."""
	_assert_task_access(task)
	rows = frappe.get_all(
		"HD Task Comment",
		filters={"task": task},
		fields=["name", "content", "owner", "creation"],
		order_by="creation asc",
		ignore_permissions=True,
	)
	owners = list({r.owner for r in rows if r.owner})
	names, agents = {}, set()
	if owners:
		names = {
			u.name: u.full_name
			for u in frappe.get_all(
				"User", filters={"name": ["in", owners]}, fields=["name", "full_name"]
			)
		}
		agents = set(
			frappe.get_all("HD Agent", filters={"name": ["in", owners]}, pluck="name")
		)
	agent = is_agent()
	for r in rows:
		r["author"] = names.get(r.owner) or r.owner
		r["is_agent"] = r.owner in agents
		if not agent:
			# owner is an email address; don't expose it on the portal.
			r["owner"] = None
	return rows


@frappe.whitelist()
def add_task_comment(task: str, content: str) -> str:
	"""Post a comment on a task. Agents and the parent's customer."""
	_assert_task_access(task)
	content = (content or "").strip()
	if not content:
		frappe.throw(_("Comment cannot be empty"))
	c = frappe.get_doc(
		{"doctype": "HD Task Comment", "task": task, "content": content}
	).insert(ignore_permissions=True)
	return c.name
