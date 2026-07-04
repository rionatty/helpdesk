# Add-ons API.
#
# Agent Managers see every add-on; other agents only the ones they are
# assigned to (HD Addon Member). Customers view their own company's add-ons
# (read-only). Access is checked explicitly, then queries run with
# ignore_permissions.

import frappe
from frappe import _
from frappe.utils import cint

from helpdesk.utils import (
	agent_has_addon,
	agent_has_project,
	assigned_addon_names,
	get_customer,
	get_doc_viewers,
	is_agent,
	is_agent_manager,
	log_doc_view,
)

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
def get_addons(customer: str | None = None, mine: bool = False) -> list:
	"""List add-ons. Agent Managers see all (optionally by customer/mine);
	other agents see only add-ons they are assigned to; customers see only
	their company's add-ons."""
	filters: dict = {}
	if customer:
		filters["customer"] = customer
	if not is_agent():
		companies = get_customer(frappe.session.user)
		if not companies:
			return []
		filters["customer"] = ["in", companies]
	elif not is_agent_manager() or mine:
		# Non-manager agents are limited to their assigned add-ons; managers
		# can opt into the same "just mine" view via `mine`.
		my_addons = assigned_addon_names()
		if not my_addons:
			return []
		filters["name"] = ["in", my_addons]
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
	# The creator is assigned automatically so they can open what they created.
	user = frappe.session.user
	if frappe.db.exists("HD Agent", user):
		frappe.get_doc(
			{"doctype": "HD Addon Member", "addon": doc.name, "agent": user}
		).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_addon(name: str, **fields) -> bool:
	"""Update writable add-on fields. Assigned agents and managers only."""
	_assert_agent()
	_assert_addon_access(name)
	doc = frappe.get_doc("HD Addon", name)
	for key, value in fields.items():
		if key in WRITABLE:
			doc.set(key, value)
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_addon(name: str) -> bool:
	"""Delete an add-on and its features/tasks (incl. their comments).
	Agent Managers only — deletion is destructive."""
	_assert_agent()
	if not is_agent_manager():
		frappe.throw(
			_("Only Agent Managers can delete an add-on"), frappe.PermissionError
		)
	frappe.db.delete("HD Addon Member", {"addon": name})
	frappe.db.delete("HD Addon Feature", {"addon": name})
	tasks = frappe.get_all("HD Addon Task", filters={"addon": name}, pluck="name")
	if tasks:
		frappe.db.delete("HD Task Comment", {"task": ["in", tasks]})
		frappe.db.delete("HD Addon Task", {"addon": name})
	frappe.delete_doc("HD Addon", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_addon_members(addon: str) -> list[dict]:
	"""List agents assigned to an add-on. Assigned agents and managers only."""
	_assert_agent()
	_assert_addon_access(addon)
	rows = frappe.get_all(
		"HD Addon Member",
		filters={"addon": addon},
		fields=["name", "agent"],
		ignore_permissions=True,
	)
	for r in rows:
		r["agent_name"] = (
			frappe.db.get_value("HD Agent", r.agent, "agent_name") or r.agent
		)
	return rows


@frappe.whitelist()
def add_addon_member(addon: str, agent: str) -> str:
	"""Assign an agent to an add-on. Only managers and agents already on the
	add-on can extend the roster. Silently skips duplicates."""
	_assert_agent()
	_assert_addon_access(addon)
	if not frappe.db.exists("HD Agent", agent):
		frappe.throw(_("Agent not found"), frappe.DoesNotExistError)
	if frappe.db.exists("HD Addon Member", {"addon": addon, "agent": agent}):
		return ""
	doc = frappe.get_doc(
		{"doctype": "HD Addon Member", "addon": addon, "agent": agent}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def remove_addon_member(name: str) -> bool:
	"""Remove an agent assignment from an add-on. Only managers and agents on
	the add-on can edit the roster."""
	_assert_agent()
	addon = frappe.db.get_value("HD Addon Member", name, "addon")
	if not addon:
		return True
	_assert_addon_access(addon)
	frappe.delete_doc("HD Addon Member", name, ignore_permissions=True)
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
	"reviewer",
	"score",
	"owner",
	"milestone",
	"feature",
	"ticket",
	"is_internal",
	"start_date",
	"end_date",
	"description",
]
# `score` is deliberately NOT writable here — update_task gates it so only
# the task's reviewer (or a manager) can score.
TASK_WRITABLE = {
	"subject",
	"status",
	"priority",
	"assigned_to",
	"reviewer",
	"milestone",
	"feature",
	"ticket",
	"is_internal",
	"start_date",
	"end_date",
	"description",
}


def _assert_addon_access(addon: str) -> frappe._dict:
	"""Managers and assigned agents; customers only for their own company's
	add-ons."""
	row = frappe.db.get_value("HD Addon", addon, ["name", "customer"], as_dict=True)
	if not row:
		frappe.throw(_("Add-on not found"), frappe.DoesNotExistError)
	if is_agent():
		if agent_has_addon(addon):
			return row
		frappe.throw(
			_("You are not assigned to this add-on"), frappe.PermissionError
		)
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
	"""Tasks for an add-on, a project, or standalone (neither), with assignee/
	reviewer names + comment counts. Portal users don't get internal tasks,
	agent emails, nor review data (reviewer/score are internal QA)."""
	agent = is_agent()
	or_filters = None
	if addon:
		filters: dict = {"addon": addon}
	elif project:
		filters = {"project": project}
	else:
		# Standalone tasks — the independent Tasks workspace. Non-managers
		# only see tasks they created, are assigned to, or review.
		filters = {"addon": ["is", "not set"], "project": ["is", "not set"]}
		if not is_agent_manager():
			me = frappe.session.user
			or_filters = [
				["owner", "=", me],
				["assigned_to", "=", me],
				["reviewer", "=", me],
			]
	if not agent:
		filters["is_internal"] = 0
	try:
		rows = frappe.get_all(
			"HD Addon Task",
			filters=filters,
			or_filters=or_filters,
			fields=TASK_FIELDS,
			order_by="modified desc",
			ignore_permissions=True,
		)
	except Exception:
		return []
	users = list(
		{r.assigned_to for r in rows if r.assigned_to}
		| {r.reviewer for r in rows if r.reviewer}
	)
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
			# Count in Python — string aggregates in `fields` are rejected on
			# Frappe v16, and comment volumes per task list are tiny.
			for task_name in frappe.get_all(
				"HD Task Comment",
				filters={"task": ["in", [r.name for r in rows]]},
				pluck="task",
				ignore_permissions=True,
			):
				counts[task_name] = counts.get(task_name, 0) + 1
		except Exception:
			counts = {}
	for r in rows:
		# Assignees are agents; never fall back to their email on the portal.
		r["assigned_to_name"] = names.get(r.assigned_to) or (
			r.assigned_to if agent else (_("Support agent") if r.assigned_to else None)
		)
		r["reviewer_name"] = (
			(names.get(r.reviewer) or r.reviewer) if agent and r.reviewer else None
		)
		r["comment_count"] = counts.get(r.name, 0)
		if not agent:
			# assigned_to/owner are emails; the portal gets display names only.
			# Reviewer and score are internal QA — never shown to customers.
			r["assigned_to"] = None
			r["owner"] = None
			r["reviewer"] = None
			r["score"] = 0
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
			if agent_has_project(project):
				return
			frappe.throw(
				_("You are not assigned to this project"), frappe.PermissionError
			)
		if (row.project_type or "Customer") == "Internal":
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		if row.customer and row.customer in get_customer(frappe.session.user):
			return
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	# No parent — a standalone task in the independent Tasks workspace.
	# Internal to the team: agents only, never the portal.
	_assert_agent()


def _assert_task_access(task: str) -> frappe._dict:
	row = frappe.db.get_value(
		"HD Addon Task",
		task,
		["addon", "project", "owner", "assigned_to", "reviewer"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Task not found"), frappe.DoesNotExistError)
	# The agents directly involved (creator, assignee, reviewer) can always
	# reach a task, even if they aren't full members of its parent.
	user = frappe.session.user
	if is_agent() and (
		is_agent_manager() or user in (row.owner, row.assigned_to, row.reviewer)
	):
		return row
	if row.addon or row.project:
		# Otherwise fall back to parent access (covers the parent's customer).
		_assert_parent_access(addon=row.addon, project=row.project)
		return row
	# Standalone task with no involvement.
	_assert_agent()
	frappe.throw(_("You do not have access to this task"), frappe.PermissionError)


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
	log_doc_view("HD Addon", name)
	if is_agent():
		doc["viewers"] = get_doc_viewers("HD Addon", name)
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
	"""Update a feature (incl. tagging it to a project). Assigned agents and
	managers only."""
	_assert_agent()
	doc = frappe.get_doc("HD Addon Feature", name)
	_assert_addon_access(doc.addon)
	for key, value in fields.items():
		if key in FEATURE_WRITABLE:
			doc.set(key, value or None if key == "project" else value)
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_feature(name: str) -> bool:
	"""Delete a feature. Assigned agents and managers only."""
	_assert_agent()
	addon = frappe.db.get_value("HD Addon Feature", name, "addon")
	if addon:
		_assert_addon_access(addon)
	frappe.delete_doc("HD Addon Feature", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_tasks(addon: str | None = None, project: str | None = None) -> list:
	"""Tasks for an add-on or project (agents and the parent's customer), or —
	with no parent — the standalone Tasks workspace (agents only; non-managers
	see the tasks they created, are assigned to, or review)."""
	_assert_parent_access(addon=addon, project=project)
	return _get_tasks(addon=addon, project=project)


def _grant_task_access(doc) -> None:
	"""Assigning a task (or naming a reviewer) grants that agent access to the
	parent, so they can actually open the project/add-on and see their task.
	No-op for standalone tasks (no parent to join)."""
	people = [p for p in (doc.get("assigned_to"), doc.get("reviewer")) if p]
	if not people:
		return
	if doc.get("project"):
		member_doctype, parent_field, parent = (
			"HD Project Member",
			"project",
			doc.project,
		)
	elif doc.get("addon"):
		member_doctype, parent_field, parent = "HD Addon Member", "addon", doc.addon
	else:
		return
	for agent in people:
		if not frappe.db.exists("HD Agent", agent):
			continue
		if frappe.db.exists(member_doctype, {parent_field: parent, "agent": agent}):
			continue
		frappe.get_doc(
			{"doctype": member_doctype, parent_field: parent, "agent": agent}
		).insert(ignore_permissions=True)


def _notify_task_assignee(doc) -> None:
	"""Email the assignee that a task was assigned to them. Best-effort: never
	break the save if mail isn't configured. Skips self-assignment."""
	agent = doc.get("assigned_to")
	if not agent or agent == frappe.session.user or agent == "Guest":
		return
	try:
		agent_name = (
			frappe.db.get_value("HD Agent", agent, "agent_name") or agent
		).split(" ")[0]
		if doc.get("project"):
			context = frappe.db.get_value("HD Project", doc.project, "project_name")
			link = frappe.utils.get_url(f"/helpdesk/projects/{doc.project}")
		elif doc.get("addon"):
			context = frappe.db.get_value("HD Addon", doc.addon, "addon_name")
			link = frappe.utils.get_url(f"/helpdesk/addons/{doc.addon}")
		else:
			context = _("Tasks")
			link = frappe.utils.get_url("/helpdesk/tasks")
		assigner = (
			frappe.db.get_value("HD Agent", frappe.session.user, "agent_name")
			or frappe.session.user
		)
		subject = _("You've been assigned a task: {0}").format(doc.subject)
		message = f"""
			<p>{_('Hi')} {frappe.utils.escape_html(agent_name)},</p>
			<p>{frappe.utils.escape_html(assigner)} {_('assigned you a task')}
			{_('in')} <strong>{frappe.utils.escape_html(context or '')}</strong>:</p>
			<p style="font-size:15px;font-weight:600;margin:12px 0;">
				{frappe.utils.escape_html(doc.subject)}</p>
			<p><strong>{_('Priority')}:</strong> {frappe.utils.escape_html(doc.get('priority') or 'Medium')}
			&nbsp;·&nbsp; <strong>{_('Status')}:</strong> {frappe.utils.escape_html(doc.get('status') or 'To Do')}
			{('&nbsp;·&nbsp; <strong>' + _('Due') + ':</strong> ' + str(doc.end_date)) if doc.get('end_date') else ''}</p>
			<p style="margin-top:16px;">
				<a href="{link}" style="background:#2563eb;color:#fff;padding:8px 16px;
				border-radius:6px;text-decoration:none;">{_('Open task')}</a>
			</p>
		"""
		frappe.sendmail(
			recipients=[agent],
			subject=subject,
			message=message,
			reference_doctype="HD Addon Task",
			reference_name=doc.name,
		)
	except Exception:
		frappe.log_error(
			title="Task assignment email failed",
			message=frappe.get_traceback(),
		)


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
	reviewer: str | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	description: str | None = None,
	is_internal: int = 0,
) -> str:
	"""Add a task to an add-on, a project, or standalone (no parent).
	Agents only."""
	_assert_agent()
	_assert_parent_access(addon=addon, project=project)
	if not (subject or "").strip():
		frappe.throw(_("Task title is required"))
	if milestone and project:
		if frappe.db.get_value("HD Milestone", milestone, "project") != project:
			frappe.throw(_("Milestone belongs to a different project"))
	# Standalone (Tasks workspace): default the assignee to the creator, and
	# stop non-managers from assigning work to anyone but themselves.
	if not addon and not project:
		if not assigned_to:
			assigned_to = frappe.session.user
		elif not is_agent_manager() and assigned_to != frappe.session.user:
			frappe.throw(
				_("Only managers can assign tasks to other agents"),
				frappe.PermissionError,
			)
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
			"reviewer": reviewer or None,
			"start_date": start_date,
			"end_date": end_date,
			"description": description,
			"is_internal": 1 if cint(is_internal) else 0,
		}
	).insert(ignore_permissions=True)
	_grant_task_access(doc)
	if doc.assigned_to:
		_notify_task_assignee(doc)
	return doc.name


@frappe.whitelist()
def update_task(name: str, **fields) -> bool:
	"""Update a task. Assigned agents and managers only. Scoring is reserved
	for the task's reviewer (or a manager)."""
	_assert_agent()
	_assert_task_access(name)
	doc = frappe.get_doc("HD Addon Task", name)
	old_assignee = doc.assigned_to
	# Standalone tasks: only managers may reassign to someone else.
	if (
		"assigned_to" in fields
		and not doc.addon
		and not doc.project
		and not is_agent_manager()
		and fields.get("assigned_to")
		and fields.get("assigned_to") != frappe.session.user
	):
		frappe.throw(
			_("Only managers can assign tasks to other agents"),
			frappe.PermissionError,
		)
	score = fields.pop("score", None)
	if score is not None:
		# Check against the reviewer as stored, not one set in this request.
		if not (is_agent_manager() or frappe.session.user == doc.reviewer):
			frappe.throw(
				_("Only the reviewer or a manager can score a task"),
				frappe.PermissionError,
			)
		doc.score = max(0, min(5, cint(score)))
	for key, value in fields.items():
		if key in TASK_WRITABLE:
			doc.set(key, value)
	if doc.milestone and doc.project:
		if frappe.db.get_value("HD Milestone", doc.milestone, "project") != doc.project:
			frappe.throw(_("Milestone belongs to a different project"))
	doc.save(ignore_permissions=True)
	# Grant the (possibly new) assignee/reviewer access to the parent, and
	# notify the assignee if it changed to someone new.
	_grant_task_access(doc)
	if doc.assigned_to and doc.assigned_to != old_assignee:
		_notify_task_assignee(doc)
	return True


@frappe.whitelist()
def delete_task(name: str) -> bool:
	"""Delete a task and its comments. Assigned agents and managers only."""
	_assert_agent()
	_assert_task_access(name)
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
			# owner is an email address; don't expose it on the portal. Agents
			# without a display name get a generic label instead of their email.
			if r["is_agent"] and not names.get(r.owner):
				r["author"] = _("Support agent")
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
