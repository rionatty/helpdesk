# Tasks hub API.
#
# Powers the independent Tasks workspace. Agents see the tasks they created,
# are assigned to, or review; Agent Managers and admins see every task. Tasks
# from projects/add-ons are included (read-only placement) alongside standalone
# tasks, so the hub is a single place to see "everything on my plate".

import frappe
from frappe import _

from helpdesk.api.addon import TASK_FIELDS
from helpdesk.utils import is_agent, is_agent_manager

HUB_FIELDS = TASK_FIELDS + ["addon", "project"]


@frappe.whitelist()
def get_my_tasks() -> list:
	"""Tasks visible to the current agent. Managers/admins get all; other
	agents get the tasks they own, are assigned to, or review — enriched with
	assignee/reviewer names, the parent's label, comment counts and score."""
	if not is_agent():
		frappe.throw(_("Only agents can view tasks"), frappe.PermissionError)

	or_filters = None
	if not is_agent_manager():
		me = frappe.session.user
		or_filters = [
			["owner", "=", me],
			["assigned_to", "=", me],
			["reviewer", "=", me],
		]
	rows = frappe.get_all(
		"HD Addon Task",
		filters={},
		or_filters=or_filters,
		fields=HUB_FIELDS,
		order_by="modified desc",
		ignore_permissions=True,
	)
	if not rows:
		return []

	# Resolve agent display names for assignees and reviewers.
	people = list(
		{r.assigned_to for r in rows if r.assigned_to}
		| {r.reviewer for r in rows if r.reviewer}
	)
	name_map = {}
	if people:
		name_map = {
			a.name: a.agent_name
			for a in frappe.get_all(
				"HD Agent", filters={"name": ["in", people]}, fields=["name", "agent_name"]
			)
		}

	# Parent labels (project / add-on) for the "view by project" grouping.
	projects = list({r.project for r in rows if r.project})
	proj_names = {}
	if projects:
		proj_names = {
			p.name: p.project_name
			for p in frappe.get_all(
				"HD Project", filters={"name": ["in", projects]},
				fields=["name", "project_name"],
			)
		}
	addons = list({r.addon for r in rows if r.addon})
	addon_names = {}
	if addons:
		addon_names = {
			a.name: a.addon_name
			for a in frappe.get_all(
				"HD Addon", filters={"name": ["in", addons]},
				fields=["name", "addon_name"],
			)
		}

	# Comment counts (Python-side — string aggregates are rejected on v16).
	counts: dict = {}
	for task_name in frappe.get_all(
		"HD Task Comment",
		filters={"task": ["in", [r.name for r in rows]]},
		pluck="task",
		ignore_permissions=True,
	):
		counts[task_name] = counts.get(task_name, 0) + 1

	for r in rows:
		r["assigned_to_name"] = name_map.get(r.assigned_to) or r.assigned_to
		r["reviewer_name"] = name_map.get(r.reviewer) or r.reviewer
		if r.project:
			r["parent_type"] = "project"
			r["parent_name"] = r.project
			r["parent_label"] = proj_names.get(r.project) or r.project
		elif r.addon:
			r["parent_type"] = "addon"
			r["parent_name"] = r.addon
			r["parent_label"] = addon_names.get(r.addon) or r.addon
		else:
			r["parent_type"] = "standalone"
			r["parent_name"] = None
			r["parent_label"] = _("Personal")
		r["comment_count"] = counts.get(r.name, 0)
	return rows
