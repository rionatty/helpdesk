# Projects API.
#
# Agents (our side) manage projects fully. Customers (portal) may view and
# comment on projects that belong to their company — resolved via get_customer.
# Reads/writes use ignore_permissions AFTER an explicit access check, so portal
# users don't need direct doctype permissions.

import frappe
from frappe import _

from helpdesk.utils import get_customer, is_agent

PROJECT_FIELDS = [
	"name",
	"project_name",
	"customer",
	"status",
	"progress",
	"start_date",
	"end_date",
	"team",
	"description",
	"modified",
]

WRITABLE = {
	"project_name",
	"customer",
	"status",
	"team",
	"start_date",
	"end_date",
	"progress",
	"description",
}


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage projects"), frappe.PermissionError)


def _assert_project_access(doc) -> None:
	"""Agents always; customers only for their own company's projects."""
	if is_agent():
		return
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
	for r in rows:
		r["author"] = full_names.get(r.owner) or r.owner
		r["is_agent"] = r.owner in agents
	return rows


@frappe.whitelist()
def get_projects(customer: str | None = None) -> list:
	"""List projects. Agents see all (optionally filtered by customer);
	customers see only their company's projects."""
	filters: dict = {}
	if customer:
		filters["customer"] = customer
	if not is_agent():
		companies = get_customer(frappe.session.user)
		if not companies:
			return []
		filters["customer"] = ["in", companies]
	return frappe.get_all(
		"HD Project",
		filters=filters,
		fields=PROJECT_FIELDS,
		order_by="modified desc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def get_project(name: str) -> dict:
	"""A single project with its linked tickets and comments."""
	doc = frappe.get_doc("HD Project", name)
	_assert_project_access(doc)
	from helpdesk.api.addon import _get_tasks

	data = doc.as_dict()
	data["tickets"] = _linked_tickets(name)
	data["comments"] = _get_comments(name)
	data["features"] = _project_features(name)
	data["tasks"] = _get_tasks(project=name)
	return data


@frappe.whitelist()
def create_project(
	project_name: str,
	customer: str,
	status: str = "Planned",
	team: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	progress: int = 0,
	description: str | None = None,
) -> str:
	"""Create a project. Agents only."""
	_assert_agent()
	if not (project_name or "").strip():
		frappe.throw(_("Project name is required"))
	if not customer:
		frappe.throw(_("Customer is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Project",
			"project_name": project_name.strip(),
			"customer": customer,
			"status": status or "Planned",
			"team": team,
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
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_project(name: str) -> bool:
	"""Delete a project (and its comments). Agents only."""
	_assert_agent()
	frappe.db.delete("HD Project Comment", {"project": name})
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
