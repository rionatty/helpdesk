# Projects API.
#
# Agents (our side) manage projects fully. Customers (portal) may view and
# comment on projects that belong to their company — resolved via get_customer.
# Reads/writes use ignore_permissions AFTER an explicit access check, so portal
# users don't need direct doctype permissions.

import frappe
from frappe import _
from frappe.utils import cint, today

from helpdesk.utils import get_customer, is_agent

PROJECT_FIELDS = [
	"name",
	"project_name",
	"project_type",
	"customer",
	"status",
	"priority",
	"progress",
	"start_date",
	"end_date",
	"team",
	"lead",
	"description",
	"modified",
]

WRITABLE = {
	"project_name",
	"project_type",
	"customer",
	"status",
	"priority",
	"team",
	"lead",
	"start_date",
	"end_date",
	"progress",
	"description",
}

MILESTONE_FIELDS = [
	"name",
	"title",
	"project",
	"status",
	"due_date",
	"sequence",
	"completed_on",
	"customer_visible",
	"description",
]

MILESTONE_WRITABLE = {
	"title",
	"status",
	"due_date",
	"sequence",
	"completed_on",
	"customer_visible",
	"description",
}


def _is_internal(doc_or_row) -> bool:
	# Rows from before the field existed have project_type NULL → Customer.
	return (doc_or_row.get("project_type") or "Customer") == "Internal"


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage projects"), frappe.PermissionError)


def _assert_project_access(doc) -> None:
	"""Agents always; customers only for their own company's customer projects.
	Internal projects are never visible on the portal."""
	if is_agent():
		return
	if _is_internal(doc):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if doc.customer and doc.customer in get_customer(frappe.session.user):
		return
	frappe.throw(_("Not permitted"), frappe.PermissionError)


def _linked_tickets(project: str) -> list:
	try:
		return frappe.get_all(
			"HD Ticket",
			filters={"project": project},
			fields=["name", "subject", "status"],
			order_by="modified desc",
			ignore_permissions=True,
		)
	except Exception:
		# `project` field may not exist yet (pre-migrate); fail soft.
		return []


def _project_features(project: str) -> list:
	"""Add-on features tagged to this project (its upcoming features)."""
	return frappe.get_all(
		"HD Addon Feature",
		filters={"project": project},
		fields=["name", "feature_title", "status", "addon", "target_date"],
		order_by="creation asc",
		ignore_permissions=True,
	)


def _get_comments(project: str) -> list:
	rows = frappe.get_all(
		"HD Project Comment",
		filters={"project": project},
		fields=["name", "content", "owner", "creation"],
		order_by="creation asc",
		ignore_permissions=True,
	)
	users = list({r.owner for r in rows if r.owner})
	full_names, agents = {}, set()
	if users:
		full_names = {
			u.name: u.full_name
			for u in frappe.get_all(
				"User", filters={"name": ["in", users]}, fields=["name", "full_name"]
			)
		}
		agents = set(
			frappe.get_all(
				"HD Agent", filters={"name": ["in", users]}, pluck="name"
			)
		)
	viewer_is_agent = is_agent()
	for r in rows:
		r["author"] = full_names.get(r.owner) or r.owner
		r["is_agent"] = r.owner in agents
		if not viewer_is_agent:
			# owner is an email address; don't expose it on the portal. Agents
			# without a display name get a generic label instead of their email.
			if r["is_agent"] and not full_names.get(r.owner):
				r["author"] = _("Support agent")
			r["owner"] = None
	return rows


@frappe.whitelist()
def get_projects(
	customer: str | None = None,
	project_type: str | None = None,
	mine: bool = False,
) -> list:
	"""List projects. Agents see all (optionally filtered by customer/type/mine);
	customers see only their company's customer projects."""
	filters: dict = {}
	if customer:
		filters["customer"] = customer
	if project_type and is_agent():
		filters["project_type"] = project_type
	if not is_agent():
		companies = get_customer(frappe.session.user)
		if not companies:
			return []
		filters["customer"] = ["in", companies]
	if mine and is_agent():
		me = frappe.session.user
		member_projects = frappe.get_all(
			"HD Project Member",
			filters={"agent": me},
			pluck="project",
			ignore_permissions=True,
		)
		lead_projects = frappe.get_all(
			"HD Project",
			filters={"lead": me},
			pluck="name",
			ignore_permissions=True,
		)
		my_projects = list(set(member_projects) | set(lead_projects))
		if not my_projects:
			return []
		filters["name"] = ["in", my_projects]
	rows = frappe.get_all(
		"HD Project",
		filters=filters,
		fields=PROJECT_FIELDS,
		order_by="modified desc",
		ignore_permissions=True,
	)
	if not is_agent():
		# Defense in depth: never leak internal projects to the portal,
		# even if one was (mis)tagged with a customer.
		rows = [r for r in rows if not _is_internal(r)]
		for r in rows:
			r["lead"] = None
	return rows


@frappe.whitelist()
def get_project(name: str) -> dict:
	"""A single project with its linked tickets, comments, milestones and tasks."""
	doc = frappe.get_doc("HD Project", name)
	_assert_project_access(doc)
	from helpdesk.api.addon import _get_tasks

	data = doc.as_dict()
	data["tickets"] = _linked_tickets(name)
	data["comments"] = _get_comments(name)
	data["features"] = _project_features(name)
	data["tasks"] = _get_tasks(project=name)
	data["milestones"] = _get_milestones(name)
	data["lead_name"] = (
		frappe.db.get_value("HD Agent", doc.lead, "agent_name") if doc.lead else None
	)
	if not is_agent():
		# lead is an agent email; the portal gets the display name only.
		data["lead"] = None
	return data


@frappe.whitelist()
def create_project(
	project_name: str,
	customer: str | None = None,
	project_type: str = "Customer",
	status: str = "Planned",
	priority: str = "Medium",
	team: str | None = None,
	lead: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	progress: int = 0,
	description: str | None = None,
) -> str:
	"""Create a project. Agents only. Customer projects need a customer;
	internal projects must not have one (they'd leak to the portal)."""
	_assert_agent()
	if not (project_name or "").strip():
		frappe.throw(_("Project name is required"))
	project_type = project_type or "Customer"
	if project_type == "Customer" and not customer:
		frappe.throw(_("Customer is required for customer projects"))
	if project_type == "Internal":
		customer = None
	doc = frappe.get_doc(
		{
			"doctype": "HD Project",
			"project_name": project_name.strip(),
			"project_type": project_type,
			"customer": customer,
			"status": status or "Planned",
			"priority": priority or "Medium",
			"team": team,
			"lead": lead,
			"start_date": start_date,
			"end_date": end_date,
			"progress": progress or 0,
			"description": description,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_project(name: str, **fields) -> bool:
	"""Update writable project fields. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Project", name)
	for key, value in fields.items():
		if key in WRITABLE:
			doc.set(key, value)
	if (doc.project_type or "Customer") == "Customer" and not doc.customer:
		frappe.throw(_("Customer is required for customer projects"))
	if doc.project_type == "Internal":
		doc.customer = None
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_project(name: str) -> bool:
	"""Delete a project with its comments, milestones and tasks. Agents only."""
	_assert_agent()
	frappe.db.delete("HD Project Comment", {"project": name})
	frappe.db.delete("HD Project Member", {"project": name})
	tasks = frappe.get_all(
		"HD Addon Task", filters={"project": name}, pluck="name"
	)
	if tasks:
		frappe.db.delete("HD Task Comment", {"task": ["in", tasks]})
		frappe.db.delete("HD Addon Task", {"project": name})
	milestones = frappe.get_all(
		"HD Milestone", filters={"project": name}, pluck="name"
	)
	if milestones:
		# Unlink features pointing at these milestones before dropping them.
		frappe.db.set_value(
			"HD Addon Feature",
			{"milestone": ["in", milestones]},
			"milestone",
			None,
			update_modified=False,
		)
		frappe.db.delete("HD Milestone", {"project": name})
	frappe.db.set_value(
		"HD Addon Feature",
		{"project": name},
		"project",
		None,
		update_modified=False,
	)
	frappe.delete_doc("HD Project", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_project_comments(project: str) -> list:
	"""Comments on a project. Agents and the project's customer."""
	doc = frappe.get_doc("HD Project", project)
	_assert_project_access(doc)
	return _get_comments(project)


@frappe.whitelist()
def add_project_comment(project: str, content: str) -> str:
	"""Post a comment on a project. Agents and the project's customer."""
	doc = frappe.get_doc("HD Project", project)
	_assert_project_access(doc)
	content = (content or "").strip()
	if not content:
		frappe.throw(_("Comment cannot be empty"))
	c = frappe.get_doc(
		{"doctype": "HD Project Comment", "project": project, "content": content}
	).insert(ignore_permissions=True)
	return c.name


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


def _get_milestones(project: str) -> list:
	"""Milestones for a project, with task rollups. Customers only see
	customer-visible ones; their rollups also exclude internal tasks."""
	try:
		filters: dict = {"project": project}
		if not is_agent():
			filters["customer_visible"] = 1
		rows = frappe.get_all(
			"HD Milestone",
			filters=filters,
			fields=MILESTONE_FIELDS,
			order_by="sequence asc, due_date asc, creation asc",
			ignore_permissions=True,
		)
	except Exception:
		# Table may not exist yet (pre-migrate); fail soft.
		return []
	if not rows:
		return []
	task_filters: dict = {"milestone": ["in", [r.name for r in rows]]}
	if not is_agent():
		task_filters["is_internal"] = 0
	tasks = frappe.get_all(
		"HD Addon Task",
		filters=task_filters,
		fields=["milestone", "subject", "status"],
		order_by="creation asc",
		ignore_permissions=True,
	)
	totals: dict = {}
	task_lists: dict = {}
	for t in tasks:
		bucket = totals.setdefault(t.milestone, {"total": 0, "done": 0})
		bucket["total"] += 1
		if t.status == "Done":
			bucket["done"] += 1
		task_lists.setdefault(t.milestone, []).append(
			{"subject": t.subject, "status": t.status}
		)
	for r in rows:
		bucket = totals.get(r.name, {"total": 0, "done": 0})
		r["tasks_total"] = bucket["total"]
		r["tasks_done"] = bucket["done"]
		r["tasks"] = task_lists.get(r.name, [])
	return rows


@frappe.whitelist()
def get_milestones(project: str) -> list:
	"""Milestones of a project. Agents and the project's customer."""
	doc = frappe.get_doc("HD Project", project)
	_assert_project_access(doc)
	return _get_milestones(project)


@frappe.whitelist()
def add_milestone(
	project: str,
	title: str,
	status: str = "Upcoming",
	due_date: str | None = None,
	sequence: int = 0,
	customer_visible: int = 1,
	description: str | None = None,
) -> str:
	"""Add a milestone to a project. Agents only."""
	_assert_agent()
	if not frappe.db.exists("HD Project", project):
		frappe.throw(_("Project not found"), frappe.DoesNotExistError)
	if not (title or "").strip():
		frappe.throw(_("Milestone title is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Milestone",
			"project": project,
			"title": title.strip(),
			"status": status or "Upcoming",
			"due_date": due_date or None,
			"sequence": sequence or 0,
			"customer_visible": 1 if cint(customer_visible) else 0,
			"description": description,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_milestone(name: str, **fields) -> bool:
	"""Update a milestone. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Milestone", name)
	for key, value in fields.items():
		if key in MILESTONE_WRITABLE:
			doc.set(key, value)
	if doc.status == "Completed" and not doc.completed_on:
		doc.completed_on = today()
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_milestone(name: str) -> bool:
	"""Delete a milestone; its tasks and features are unlinked, not deleted.
	Agents only."""
	_assert_agent()
	for doctype in ("HD Addon Task", "HD Addon Feature"):
		frappe.db.set_value(
			doctype, {"milestone": name}, "milestone", None, update_modified=False
		)
	frappe.delete_doc("HD Milestone", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_project_members(project: str) -> list[dict]:
	"""List agents assigned to a project. Agents only."""
	_assert_agent()
	rows = frappe.get_all(
		"HD Project Member",
		filters={"project": project},
		fields=["name", "agent"],
		ignore_permissions=True,
	)
	for r in rows:
		r["agent_name"] = (
			frappe.db.get_value("HD Agent", r.agent, "agent_name") or r.agent
		)
	return rows


@frappe.whitelist()
def add_project_member(project: str, agent: str) -> str:
	"""Assign an agent to a project. Agents only. Silently skips duplicates."""
	_assert_agent()
	if not frappe.db.exists("HD Project", project):
		frappe.throw(_("Project not found"), frappe.DoesNotExistError)
	if frappe.db.exists("HD Project Member", {"project": project, "agent": agent}):
		return ""
	doc = frappe.get_doc(
		{"doctype": "HD Project Member", "project": project, "agent": agent}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def remove_project_member(name: str) -> bool:
	"""Remove an agent assignment from a project. Agents only."""
	_assert_agent()
	frappe.delete_doc("HD Project Member", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_taggable_features(project: str) -> list:
	"""Features of the project's customer's add-ons, for tagging to the project.
	Agents only."""
	_assert_agent()
	customer = frappe.db.get_value("HD Project", project, "customer")
	if not customer:
		return []
	addons = frappe.get_all("HD Addon", filters={"customer": customer}, pluck="name")
	if not addons:
		return []
	return frappe.get_all(
		"HD Addon Feature",
		filters={"addon": ["in", addons]},
		fields=["name", "feature_title", "status", "addon", "project"],
		order_by="creation asc",
		ignore_permissions=True,
	)
