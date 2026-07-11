# Add-ons API.
#
# Agent Managers see every add-on; other agents only the ones they are
# assigned to (HD Addon Member). Customers view their own company's add-ons
# (read-only). Access is checked explicitly, then queries run with
# ignore_permissions.

import frappe
from frappe import _
from frappe.utils import cint, flt

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
		for t in tasks:
			_snapshot_task_audit(t)
		frappe.db.delete("HD Task Comment", {"task": ["in", tasks]})
		frappe.db.delete("HD Task Subtask", {"task": ["in", tasks]})
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
	"estimated_hours",
	"completed_on",
	"review_status",
	"customer_review",
	"customer_rating",
	"customer_reviewed_on",
	"description",
	"creation",
]
# `score`, `completed_on` and `review_status` are deliberately NOT writable
# here — update_task manages them (scoring is reviewer-gated; completed_on and
# review_status follow the status/review workflow).
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
	"estimated_hours",
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
			# Reviewer, score and review status are internal QA — never shown.
			r["assigned_to"] = None
			r["owner"] = None
			r["reviewer"] = None
			r["score"] = 0
			r["review_status"] = None
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
	"""Notify the assignee that a task was assigned to them, by email plus an
	in-app realtime popup. Best-effort: never break the save. Skips
	self-assignment."""
	agent = doc.get("assigned_to")
	if not agent or agent == frappe.session.user or agent == "Guest":
		return

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

	# In-app popup — instant, and works even when email isn't configured.
	try:
		frappe.publish_realtime(
			"helpdesk:task_assigned",
			{
				"task": doc.name,
				"subject": doc.subject,
				"assigned_by": assigner,
				"context": context,
				"link": link,
			},
			user=agent,
		)
	except Exception:
		pass

	# Resolve a usable sender. frappe.sendmail silently fails when no account is
	# flagged "Default Outgoing"; fall back to any enabled outgoing account.
	sender = frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1}, "email_id"
	)
	if not sender:
		frappe.log_error(
			title="Task assignment email skipped",
			message=(
				f"No enabled outgoing Email Account configured — cannot email "
				f"{agent} about task {doc.name}. Add one under Email Account."
			),
		)
		frappe.msgprint(
			_("Task assigned. Email not sent: no outgoing Email Account is set up."),
			indicator="orange",
			alert=True,
		)
		return

	try:
		agent_name = (
			frappe.db.get_value("HD Agent", agent, "agent_name") or agent
		).split(" ")[0]
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
		# now=True sends within the request instead of parking it in the email
		# queue — so a stopped/slow scheduler doesn't swallow the notification.
		frappe.sendmail(
			recipients=[agent],
			sender=sender,
			subject=subject,
			message=message,
			reference_doctype="HD Addon Task",
			reference_name=doc.name,
			now=True,
		)
	except Exception as e:
		# Surface the real reason (bad SMTP creds, etc.) both in the Error Log and
		# to the person assigning, but never fail the save.
		frappe.log_error(
			title="Task assignment email failed",
			message=f"To: {agent}\nSender: {sender}\nTask: {doc.name}\n\n{frappe.get_traceback()}\n{e}",
		)
		frappe.msgprint(
			_("Task assigned, but the email to {0} could not be sent: {1}").format(
				agent, str(e)
			),
			indicator="orange",
			alert=True,
		)


def _notify_task_reviewer(doc) -> None:
	"""Tell the reviewer a task is ready for their review (in-app + email).
	Best-effort; skips self-review."""
	reviewer = doc.get("reviewer")
	if not reviewer or reviewer == frappe.session.user or reviewer == "Guest":
		return
	link = frappe.utils.get_url(
		f"/helpdesk/projects/{doc.project}"
		if doc.get("project")
		else f"/helpdesk/addons/{doc.addon}"
		if doc.get("addon")
		else "/helpdesk/tasks"
	)
	try:
		frappe.publish_realtime(
			"helpdesk:task_review_requested",
			{"task": doc.name, "subject": doc.subject, "link": link},
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
		name = (
			frappe.db.get_value("HD Agent", reviewer, "agent_name") or reviewer
		).split(" ")[0]
		frappe.sendmail(
			recipients=[reviewer],
			sender=sender,
			subject=_("Review requested: {0}").format(doc.subject),
			message=f"""
				<p>{_('Hi')} {frappe.utils.escape_html(name)},</p>
				<p>{_('A task is ready for your review')}:</p>
				<p style="font-size:15px;font-weight:600;margin:12px 0;">
					{frappe.utils.escape_html(doc.subject)}</p>
				<p style="margin-top:16px;">
					<a href="{link}" style="background:#2563eb;color:#fff;padding:8px 16px;
					border-radius:6px;text-decoration:none;">{_('Review task')}</a>
				</p>
			""",
			reference_doctype="HD Addon Task",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Task review email failed", message=frappe.get_traceback()
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
		user = frappe.session.user
		if not assigned_to:
			# assigned_to links to HD Agent — only self-assign if the creator is
			# actually an agent (e.g. Administrator is a User, not an HD Agent).
			assigned_to = user if frappe.db.exists("HD Agent", user) else None
		elif not is_agent_manager() and assigned_to != user:
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
	old_status = doc.status
	score = fields.pop("score", None)
	scored_now = False
	if score is not None:
		# Check against the reviewer as stored, not one set in this request.
		if not (is_agent_manager() or frappe.session.user == doc.reviewer):
			frappe.throw(
				_("Only the reviewer or a manager can score a task"),
				frappe.PermissionError,
			)
		doc.score = max(0, min(5, cint(score)))
		scored_now = True
	for key, value in fields.items():
		if key in TASK_WRITABLE:
			doc.set(key, value)
	if doc.get("estimated_hours"):
		doc.estimated_hours = max(0, flt(doc.estimated_hours))
	if doc.milestone and doc.project:
		if frappe.db.get_value("HD Milestone", doc.milestone, "project") != doc.project:
			frappe.throw(_("Milestone belongs to a different project"))

	# --- Completion + review workflow ---
	became_done = doc.status == "Done" and old_status != "Done"
	if doc.status == "Done" and not doc.completed_on:
		doc.completed_on = frappe.utils.now()
	elif doc.status != "Done":
		doc.completed_on = None
	# Scoring marks the task reviewed; finishing a reviewed-by task queues it.
	notify_reviewer = False
	if scored_now and doc.score:
		doc.review_status = "Reviewed"
	elif became_done and doc.reviewer and doc.review_status != "Reviewed":
		doc.review_status = "Pending Review"
		notify_reviewer = True

	doc.save(ignore_permissions=True)
	# Grant the (possibly new) assignee/reviewer access to the parent, and
	# notify the assignee / reviewer as appropriate.
	_grant_task_access(doc)
	if doc.assigned_to and doc.assigned_to != old_assignee:
		_notify_task_assignee(doc)
	if notify_reviewer:
		_notify_task_reviewer(doc)
	return True


@frappe.whitelist()
def request_review(name: str) -> bool:
	"""Flag a task as ready for review and notify its reviewer. Agents only."""
	_assert_agent()
	_assert_task_access(name)
	doc = frappe.get_doc("HD Addon Task", name)
	if not doc.reviewer:
		frappe.throw(_("Set a reviewer before requesting a review"))
	doc.review_status = "Pending Review"
	doc.save(ignore_permissions=True)
	_notify_task_reviewer(doc)
	return True


# ---------------------------------------------------------------------------
# Customer review of a task
# ---------------------------------------------------------------------------


def _outgoing_sender() -> str | None:
	"""Best available outgoing sender — frappe.sendmail needs one and it isn't
	always flagged Default Outgoing."""
	return frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")


def _task_customer(doc) -> str | None:
	"""The HD Customer this task belongs to (via its add-on or project).
	Standalone tasks have none."""
	if doc.get("addon"):
		return frappe.db.get_value("HD Addon", doc.addon, "customer")
	if doc.get("project"):
		return frappe.db.get_value("HD Project", doc.project, "customer")
	return None


def _customer_contact_emails(customer: str) -> list:
	"""Email addresses of the contacts linked to an HD Customer."""
	contacts = frappe.get_all(
		"Dynamic Link",
		filters={
			"parenttype": "Contact",
			"parentfield": "links",
			"link_doctype": "HD Customer",
			"link_name": customer,
		},
		pluck="parent",
		ignore_permissions=True,
	)
	if not contacts:
		return []
	return [
		e
		for e in frappe.get_all(
			"Contact", filters={"name": ["in", contacts]}, pluck="email_id",
			ignore_permissions=True,
		)
		if e
	]


def _customer_task_link(doc) -> str:
	if doc.get("addon"):
		return frappe.utils.get_url(f"/helpdesk/my-addons/{doc.addon}")
	if doc.get("project"):
		return frappe.utils.get_url(f"/helpdesk/my-projects/{doc.project}")
	return frappe.utils.get_url("/helpdesk")


def _notify_customer_review_requested(doc, customer: str) -> None:
	"""Tell the customer a task is ready for their review (in-app + email)."""
	emails = _customer_contact_emails(customer)
	for e in emails:
		try:
			frappe.publish_realtime(
				"helpdesk:customer_review_requested",
				{"task": doc.name, "subject": doc.subject},
				user=e,
			)
		except Exception:
			pass
	if not emails:
		return
	sender = _outgoing_sender()
	if not sender:
		return
	link = _customer_task_link(doc)
	try:
		frappe.sendmail(
			recipients=emails,
			sender=sender,
			subject=_("A task is ready for your review: {0}").format(doc.subject),
			message=f"""
				<p>{_('Your CyveTech team has completed a task and would value your review')}:</p>
				<p style="font-size:15px;font-weight:600;margin:12px 0;">
					{frappe.utils.escape_html(doc.subject)}</p>
				<p style="margin-top:16px;">
					<a href="{link}" style="background:#2563eb;color:#fff;padding:8px 16px;
					border-radius:6px;text-decoration:none;">{_('Review it')}</a>
				</p>
			""",
			reference_doctype="HD Addon Task",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Customer review request email failed",
			message=frappe.get_traceback(),
		)


def _task_stakeholders(doc) -> list:
	"""Agents who should hear about customer activity on a task: its assignee,
	reviewer and creator, plus every member of the parent add-on/project (and
	the project lead). Excludes the acting user."""
	people = {doc.get("assigned_to"), doc.get("reviewer"), doc.get("owner")}
	if doc.get("addon"):
		people.update(
			frappe.get_all(
				"HD Addon Member", filters={"addon": doc.addon}, pluck="agent",
				ignore_permissions=True,
			)
		)
	elif doc.get("project"):
		people.update(
			frappe.get_all(
				"HD Project Member", filters={"project": doc.project}, pluck="agent",
				ignore_permissions=True,
			)
		)
		lead = frappe.db.get_value("HD Project", doc.project, "lead")
		if lead:
			people.add(lead)
	people.discard(None)
	people.discard(frappe.session.user)
	# Only real agents get notified (owner may be a portal user).
	if not people:
		return []
	return frappe.get_all(
		"HD Agent",
		filters={"name": ["in", list(people)], "is_active": 1},
		pluck="name",
		ignore_permissions=True,
	)


def _notify_review_submitted(doc, rating: int) -> None:
	"""Tell everyone working on the task (assignee, reviewer, parent members)
	that the customer has reviewed it."""
	recipients = _task_stakeholders(doc)
	if not recipients:
		return
	for agent in recipients:
		try:
			frappe.publish_realtime(
				"helpdesk:task_reviewed",
				{"task": doc.name, "subject": doc.subject, "rating": rating},
				user=agent,
			)
		except Exception:
			pass
	sender = _outgoing_sender()
	if not sender:
		return
	try:
		frappe.sendmail(
			recipients=recipients,
			sender=sender,
			subject=_("Customer reviewed: {0}").format(doc.subject),
			message=f"<p>{_('The customer rated')} <strong>"
			f"{frappe.utils.escape_html(doc.subject)}</strong> {rating}/5.</p>",
			reference_doctype="HD Addon Task",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Customer review notification failed",
			message=frappe.get_traceback(),
		)


def _notify_customer_comment(doc, content: str) -> None:
	"""Tell everyone working on the task that the customer commented."""
	recipients = _task_stakeholders(doc)
	if not recipients:
		return
	preview = (content or "")[:140]
	for agent in recipients:
		try:
			frappe.publish_realtime(
				"helpdesk:customer_commented",
				{"task": doc.name, "subject": doc.subject, "preview": preview},
				user=agent,
			)
		except Exception:
			pass
	sender = _outgoing_sender()
	if not sender:
		return
	link = frappe.utils.get_url(
		f"/helpdesk/addons/{doc.addon}" if doc.get("addon")
		else f"/helpdesk/projects/{doc.project}" if doc.get("project")
		else "/helpdesk/tasks"
	)
	try:
		frappe.sendmail(
			recipients=recipients,
			sender=sender,
			subject=_("Customer commented on: {0}").format(doc.subject),
			message=f"""
				<p>{_('The customer commented on')} <strong>
				{frappe.utils.escape_html(doc.subject)}</strong>:</p>
				<blockquote style="border-left:3px solid #ccc;margin:8px 0;padding:4px 12px">
					{frappe.utils.escape_html(content)}
				</blockquote>
				<p style="margin-top:12px;"><a href="{link}">{_('Open it')}</a></p>
			""",
			reference_doctype="HD Addon Task",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Customer comment notification failed",
			message=frappe.get_traceback(),
		)


@frappe.whitelist()
def request_customer_review(name: str) -> bool:
	"""Send a task to its customer for review and notify them. Agents only;
	only for tasks linked to a customer (add-on/project)."""
	_assert_agent()
	_assert_task_access(name)
	doc = frappe.get_doc("HD Addon Task", name)
	customer = _task_customer(doc)
	if not customer:
		frappe.throw(_("This task isn't linked to a customer to review it"))
	if doc.customer_review == "Reviewed":
		frappe.throw(_("The customer has already reviewed this task"))
	doc.customer_review = "Requested"
	doc.save(ignore_permissions=True)
	_notify_customer_review_requested(doc, customer)
	return True


@frappe.whitelist()
def submit_customer_review(name: str, rating: int, comment: str | None = None) -> bool:
	"""Record the customer's review of a task and lock it. Allowed for the
	task's customer while it is open for review; once reviewed it can't be
	reviewed again."""
	_assert_task_access(name)
	doc = frappe.get_doc("HD Addon Task", name)
	if doc.customer_review != "Requested":
		# Covers both "not requested yet" and "already reviewed" — once reviewed
		# a task is not available for review again.
		frappe.throw(_("This task is not open for review"))
	doc.customer_rating = max(1, min(5, cint(rating)))
	doc.customer_review = "Reviewed"
	doc.customer_reviewed_on = frappe.utils.now()
	doc.save(ignore_permissions=True)
	comment = (comment or "").strip()
	if comment:
		frappe.get_doc(
			{"doctype": "HD Task Comment", "task": name, "content": comment}
		).insert(ignore_permissions=True)
	_notify_review_submitted(doc, doc.customer_rating)
	return True


def _notify_customer_review_requested_bulk(customer: str, tasks: list) -> None:
	"""One consolidated 'these tasks are ready for your review' message per
	customer, instead of one email per task."""
	emails = _customer_contact_emails(customer)
	for e in emails:
		try:
			frappe.publish_realtime(
				"helpdesk:customer_review_requested",
				{"count": len(tasks)},
				user=e,
			)
		except Exception:
			pass
	if not emails:
		return
	sender = _outgoing_sender()
	if not sender:
		return
	items = "".join(
		f'<li style="margin:4px 0"><a href="{t["link"]}">'
		f'{frappe.utils.escape_html(t["subject"])}</a></li>'
		for t in tasks
	)
	try:
		frappe.sendmail(
			recipients=emails,
			sender=sender,
			subject=_("{0} tasks are ready for your review").format(len(tasks)),
			message=f"""
				<p>{_('Your CyveTech team has completed work and would value your review')}:</p>
				<ul style="padding-left:18px">{items}</ul>
			""",
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Customer review request email failed",
			message=frappe.get_traceback(),
		)


@frappe.whitelist()
def request_customer_review_bulk(names) -> int:
	"""Request customer review for many tasks at once, sending each customer a
	single consolidated notification. Agents only. Skips tasks with no customer
	or already reviewed. Returns the number of tasks newly requested."""
	_assert_agent()
	names = frappe.parse_json(names) if isinstance(names, str) else (names or [])
	by_customer: dict = {}
	count = 0
	for name in names:
		_assert_task_access(name)
		doc = frappe.get_doc("HD Addon Task", name)
		customer = _task_customer(doc)
		if not customer or doc.customer_review == "Reviewed":
			continue
		doc.customer_review = "Requested"
		doc.save(ignore_permissions=True)
		by_customer.setdefault(customer, []).append(
			{"subject": doc.subject, "link": _customer_task_link(doc)}
		)
		count += 1
	for cust, tasks in by_customer.items():
		_notify_customer_review_requested_bulk(cust, tasks)
	return count


@frappe.whitelist()
def bulk_update_tasks(names, **fields) -> int:
	"""Apply the same field update (status / priority / assigned_to) to many
	tasks. Reuses update_task per row, so per-task access, the completion/review
	workflow and notifications all still apply. Returns the count updated."""
	_assert_agent()
	names = frappe.parse_json(names) if isinstance(names, str) else (names or [])
	# Only allow the safe bulk fields through.
	allowed = {k: v for k, v in fields.items() if k in ("status", "priority", "assigned_to")}
	if not allowed:
		frappe.throw(_("Nothing to update"))
	count = 0
	for name in names:
		update_task(name, **allowed)
		count += 1
	return count


@frappe.whitelist()
def bulk_delete_tasks(names) -> int:
	"""Delete many tasks (each snapshotted to the audit log first). Agents
	only; per-task access is enforced by delete_task. Returns the count."""
	_assert_agent()
	names = frappe.parse_json(names) if isinstance(names, str) else (names or [])
	count = 0
	for name in names:
		delete_task(name)
		count += 1
	return count


def _snapshot_task_audit(name: str) -> None:
	"""Preserve a task's final state and change history in an immutable log
	before it's deleted, so the audit trail survives deletion. Best-effort."""
	try:
		doc = frappe.db.get_value("HD Addon Task", name, "*", as_dict=True)
		if not doc:
			return
		history = frappe.get_all(
			"Version",
			filters={"ref_doctype": "HD Addon Task", "docname": name},
			fields=["owner", "creation", "data"],
			order_by="creation asc",
			ignore_permissions=True,
		)
		frappe.get_doc(
			{
				"doctype": "HD Task Audit",
				"task": name,
				"task_subject": doc.get("subject"),
				"action": "Deleted",
				"deleted_by": frappe.session.user,
				"deleted_on": frappe.utils.now(),
				"snapshot": frappe.as_json(doc, indent=1),
				"history": frappe.as_json(history, indent=1),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title="Task audit snapshot failed", message=frappe.get_traceback()
		)


@frappe.whitelist()
def delete_task(name: str) -> bool:
	"""Delete a task with its comments and subtasks. Assigned agents and
	managers only. The audit trail is snapshotted first so it survives."""
	_assert_agent()
	_assert_task_access(name)
	_snapshot_task_audit(name)
	frappe.db.delete("HD Task Comment", {"task": name})
	frappe.db.delete("HD Task Subtask", {"task": name})
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
	"""Post a comment on a task. Agents and the parent's customer. Customer
	comments notify everyone working on the task."""
	_assert_task_access(task)
	content = (content or "").strip()
	if not content:
		frappe.throw(_("Comment cannot be empty"))
	c = frappe.get_doc(
		{"doctype": "HD Task Comment", "task": task, "content": content}
	).insert(ignore_permissions=True)
	if not is_agent():
		doc = frappe.get_doc("HD Addon Task", task)
		_notify_customer_comment(doc, content)
	return c.name


# ---------------------------------------------------------------------------
# Task audit trail (change history)
# ---------------------------------------------------------------------------

# Framework/bookkeeping fields we never want to surface in the audit timeline.
_LOG_IGNORE_FIELDS = {
	"modified",
	"modified_by",
	"creation",
	"owner",
	"_liked_by",
	"_comments",
	"_assign",
	"_seen",
	"_user_tags",
	"docstatus",
}


def _fmt_log_value(fieldname: str, value) -> str:
	"""Human-readable rendering of an old/new field value for the audit log."""
	if fieldname in ("assigned_to", "reviewer"):
		if not value:
			return "—"
		return frappe.db.get_value("HD Agent", value, "agent_name") or value
	if fieldname == "is_internal":
		return _("Yes") if cint(value) else _("No")
	if value in (None, ""):
		return "—"
	return str(value)


@frappe.whitelist()
def get_task_activity(task: str) -> list:
	"""Readable change history for a task (audit trail), newest first.

	Backed by Frappe's Version log (the doctype has track_changes on), so every
	field change is already recorded with who and when. Agents only — the trail
	exposes internal fields (reviewer, score, internal flag)."""
	_assert_agent()
	_assert_task_access(task)

	meta = frappe.get_meta("HD Addon Task")
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": "HD Addon Task", "docname": task},
		fields=["owner", "creation", "data"],
		order_by="creation desc",
		ignore_permissions=True,
	)
	created = frappe.db.get_value(
		"HD Addon Task", task, ["owner", "creation"], as_dict=True
	)

	users = {v.owner for v in versions if v.owner}
	if created and created.owner:
		users.add(created.owner)
	names, agents = {}, set()
	if users:
		names = {
			u.name: u.full_name
			for u in frappe.get_all(
				"User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"]
			)
		}
		agents = set(
			frappe.get_all("HD Agent", filters={"name": ["in", list(users)]}, pluck="name")
		)

	entries = []
	for v in versions:
		try:
			data = frappe.parse_json(v.data) or {}
		except Exception:
			continue
		changes = []
		for row in data.get("changed") or []:
			if not isinstance(row, (list, tuple)) or len(row) < 3:
				continue
			fieldname = row[0]
			if fieldname in _LOG_IGNORE_FIELDS:
				continue
			df = meta.get_field(fieldname)
			changes.append(
				{
					"field": df.label if df else fieldname,
					"from": _fmt_log_value(fieldname, row[1]),
					"to": _fmt_log_value(fieldname, row[2]),
				}
			)
		if not changes:
			continue
		entries.append(
			{
				"author": names.get(v.owner) or v.owner,
				"is_agent": v.owner in agents,
				"creation": v.creation,
				"action": "updated",
				"changes": changes,
			}
		)

	if created:
		entries.append(
			{
				"author": names.get(created.owner) or created.owner,
				"is_agent": created.owner in agents,
				"creation": created.creation,
				"action": "created",
				"changes": [],
			}
		)
	return entries
