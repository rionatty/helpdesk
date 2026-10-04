# @mentions and watchers on tasks - pull a colleague in without reassigning.
#
# Watchers are the people who hear about a task: anyone who clicked Watch,
# anyone who commented or was @mentioned, and always its assignee and
# reviewer (they're involved whether they clicked Watch or not). They're told
# about new comments and status changes, by email and an in-app toast.
#
# Mentions are agents only - the portal never sees the agent list - and a
# mention notifies that agent directly instead of as a plain watcher, so no
# one hears about the same comment twice.
#
# addon.py imports this module, so anything from addon is imported lazily.

import html

import frappe
from frappe import _
from frappe.utils import cint, get_url, strip_html

from helpdesk.utils import is_agent

# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def audiences(watchers, mentioned, actor, skip=()) -> tuple:
	"""(mention_targets, other_watchers). Nobody hears about their own action,
	a mentioned watcher gets the mention instead of a plain watcher notice, and
	`skip` drops people another email already covers."""
	skip = set(skip) | {actor}
	mention_targets = {m for m in mentioned if m} - skip
	others = {w for w in watchers if w} - mention_targets - skip
	return mention_targets, others


def email_body(headline, quote, link, reason) -> str:
	"""Escaped - comments can come from customers."""
	e = html.escape
	quote = " ".join(strip_html(str(quote or "")).split())
	if len(quote) > 400:
		quote = quote[:399].rstrip() + "…"
	quote_html = (
		'<blockquote style="margin:12px 0;padding:8px 14px;border-left:3px solid #d1d5db;'
		f'color:#374151">{e(quote)}</blockquote>'
		if quote
		else ""
	)
	return (
		'<div style="font-family:Arial,Helvetica,sans-serif;color:#1f2937">'
		f'<p style="margin:0 0 4px">{headline}</p>{quote_html}'
		f'<p><a href="{e(link)}" style="display:inline-block;background:#2563eb;color:#fff;'
		'padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:600">Open</a></p>'
		f'<p style="color:#9ca3af;font-size:12px">{e(reason)}</p></div>'
	)


# ---------------------------------------------------------------------------
# Watchers
# ---------------------------------------------------------------------------


def _explicit(task: str) -> set:
	try:
		return set(frappe.get_all("HD Task Watcher", filters={"task": task}, pluck="agent"))
	except Exception:
		return set()  # table may not exist yet (pre-migrate)


def watcher_set(doc) -> set:
	"""Everyone who should hear about this task."""
	return {p for p in _explicit(doc.name) | {doc.get("assigned_to"), doc.get("reviewer")} if p}


def _active_agents(users) -> set:
	users = {u for u in users if u}
	if not users:
		return set()
	return set(
		frappe.get_all(
			"HD Agent", filters={"name": ["in", list(users)], "is_active": 1}, pluck="name"
		)
	)


def add_watchers(task: str, users) -> None:
	for agent in _active_agents(users) - _explicit(task):
		frappe.get_doc({"doctype": "HD Task Watcher", "task": task, "agent": agent}).insert(
			ignore_permissions=True
		)


def _names(users) -> dict:
	users = [u for u in users if u]
	if not users:
		return {}
	rows = frappe.get_all(
		"HD Agent", filters={"name": ["in", users]}, fields=["name", "agent_name"]
	)
	return {r.name: r.agent_name or r.name for r in rows}


def _display(user: str) -> str:
	return (
		frappe.db.get_value("HD Agent", user, "agent_name")
		or frappe.db.get_value("User", user, "full_name")
		or user
	)


@frappe.whitelist()
def get_watchers(task: str) -> dict:
	from helpdesk.api.addon import _assert_task_access

	_assert_task_access(task)
	if not is_agent():
		# Internal: who follows a task is the team's business.
		return {"watchers": [], "watching": False, "can_unwatch": False}
	doc = frappe.get_doc("HD Addon Task", task)
	explicit = _explicit(task)
	roles = {}
	if doc.reviewer:
		roles[doc.reviewer] = _("Reviewer")
	if doc.assigned_to:
		roles[doc.assigned_to] = _("Assignee")
	people = explicit | set(roles)
	names = _names(people)
	me = frappe.session.user
	return {
		"watchers": sorted(
			({"agent": p, "name": names.get(p, p), "role": roles.get(p)} for p in people),
			key=lambda w: (w["role"] is None, w["name"].lower()),
		),
		"watching": me in people,
		# The assignee and reviewer are involved; they can't opt out.
		"can_unwatch": me in explicit and me not in roles,
	}


@frappe.whitelist()
def set_watching(task: str, watch) -> dict:
	from helpdesk.api.addon import _assert_task_access

	_assert_task_access(task)
	if not is_agent():
		frappe.throw(_("Only agents can watch tasks"), frappe.PermissionError)
	me = frappe.session.user
	if cint(watch):
		add_watchers(task, [me])
	else:
		frappe.db.delete("HD Task Watcher", {"task": task, "agent": me})
	return get_watchers(task)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def _link(doc) -> str:
	from helpdesk.integrations.pumble import _task_scope

	return get_url() + _task_scope(doc)[2]


def _email(recipients, subject, body, task) -> None:
	if recipients:
		frappe.enqueue(
			"helpdesk.api.task_collab.deliver_email",
			queue="short",
			enqueue_after_commit=True,
			recipients=sorted(recipients),
			subject=subject,
			body=body,
			task=task,
		)


def deliver_email(recipients, subject, body, task) -> None:
	"""Background job: same sender resolution as the other task emails."""
	sender = frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")
	frappe.sendmail(
		recipients=recipients,
		sender=sender,
		subject=subject,
		message=body,
		reference_doctype="HD Addon Task",
		reference_name=task,
		now=True,
	)


def _toast(users, event, payload) -> None:
	for user in users:
		try:
			frappe.publish_realtime(event, payload, user=user)
		except Exception:
			pass


def on_comment(doc, content, mentions=None) -> None:
	"""A comment was posted: notify the agents it mentions, then every other
	watcher. Commenting (as an agent) or being mentioned makes you a watcher."""
	try:
		actor = frappe.session.user
		agent = is_agent()
		if isinstance(mentions, str):
			mentions = frappe.parse_json(mentions)
		mentioned = _active_agents(mentions or []) if agent else set()
		add_watchers(doc.name, mentioned | ({actor} if agent else set()))

		mention_targets, others = audiences(watcher_set(doc), mentioned, actor)
		author = html.escape(_display(actor))
		subject = html.escape(doc.subject or "")
		link = _link(doc)
		if mention_targets:
			_email(
				mention_targets,
				_("{0} mentioned you on: {1}").format(_display(actor), doc.subject),
				email_body(
					f"<b>{author}</b> mentioned you on <b>{subject}</b>:",
					content, link, _("You're receiving this because you were mentioned."),
				),
				doc.name,
			)
			_toast(
				mention_targets,
				"helpdesk:task_mentioned",
				{"subject": doc.subject, "by": _display(actor)},
			)
		if others:
			_email(
				others,
				_("New comment on: {0}").format(doc.subject),
				email_body(
					f"<b>{author}</b> commented on <b>{subject}</b>:",
					content, link, _("You're receiving this because you watch this task."),
				),
				doc.name,
			)
			# A customer comment already toasts the task's people
			# (helpdesk:customer_commented); don't toast them twice.
			if agent:
				_toast(
					others,
					"helpdesk:task_activity",
					{"subject": doc.subject, "message": _("{0} commented").format(_display(actor))},
				)
	except Exception:
		frappe.log_error(title=f"Task comment notifications failed for {doc.name}")


def on_status_change(doc, old_status, skip=()) -> None:
	"""Tell the watchers a task moved. Skipped during bulk updates (moving 20
	tasks would otherwise send each watcher 20 emails), and for anyone another
	email already covers (`skip`)."""
	if frappe.flags.get("in_bulk_task_update"):
		return
	try:
		actor = frappe.session.user
		_, others = audiences(watcher_set(doc), (), actor, skip)
		if not others:
			return
		who = _display(actor)
		_email(
			others,
			_("{0}: {1} to {2}").format(doc.subject, old_status or "-", doc.status),
			email_body(
				f"<b>{html.escape(who)}</b> moved <b>{html.escape(doc.subject or '')}</b> "
				f"from {html.escape(old_status or '-')} to <b>{html.escape(doc.status or '')}</b>.",
				"", _link(doc), _("You're receiving this because you watch this task."),
			),
			doc.name,
		)
		_toast(
			others,
			"helpdesk:task_activity",
			{"subject": doc.subject, "message": _("{0} moved it to {1}").format(who, doc.status)},
		)
	except Exception:
		frappe.log_error(title=f"Task status notifications failed for {doc.name}")
