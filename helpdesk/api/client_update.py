# Weekly client update: one email per active project, to the client, every
# Monday morning - what's waiting on them, what got done, what's next.
#
# ERP rollouts stall on the client's side more often than ours. This turns
# the task "responsibility" field into a nudge: the client sees, in one
# email, exactly which items are waiting on them, without anyone chasing.
#
# Off until a manager enables it (HD Settings > send_weekly_client_update).
# Each project can opt out and choose its recipients. Quiet weeks send
# nothing. Only what the client can already see in the portal is included.

import html
import re
from datetime import date

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	formatdate,
	get_datetime,
	get_url,
	getdate,
	now_datetime,
	validate_email_address,
)

OPEN_PROJECT_STATUSES = ["Planned", "Active", "On Hold"]
WINDOW_DAYS = 7  # "done this week"
AHEAD_DAYS = 14  # "coming up"
RESEND_GUARD_DAYS = 5  # never twice in one week, even if the job reruns
CLIENT_SIDE = ("Client", "Joint")


# ---------------------------------------------------------------------------
# Pure parts - no database, unit-tested offline
# ---------------------------------------------------------------------------


def parse_recipients(text) -> list:
	"""Emails from a comma / semicolon / space / newline separated list, in
	order, de-duplicated case-insensitively."""
	seen, out = set(), []
	for part in re.split(r"[,;\s]+", text or ""):
		email = part.strip()
		if email and email.lower() not in seen:
			seen.add(email.lower())
			out.append(email)
	return out


def sections(milestones, tasks, today, since, ahead) -> dict:
	"""Sort what the client can see into the email's sections. Dates are
	date objects (or None); every row is a dict."""
	open_tasks = [t for t in tasks if t.get("status") != "Done"]
	waiting = sorted(
		(t for t in open_tasks if t.get("responsibility") in CLIENT_SIDE),
		key=lambda t: t.get("end_date") or date.max,
	)
	return {
		"waiting": waiting,
		"signoffs": [m for m in milestones if m.get("signoff_status") == "Requested"],
		"reviews": [t for t in tasks if t.get("customer_review") == "Requested"],
		"done_milestones": [
			m for m in milestones if m.get("completed_on") and m["completed_on"] >= since
		],
		"done_tasks": [
			t
			for t in tasks
			if t.get("status") == "Done" and t.get("completed_on") and t["completed_on"] >= since
		],
		"upcoming_milestones": [
			m
			for m in milestones
			if m.get("status") != "Completed"
			and m.get("due_date")
			and today <= m["due_date"] <= ahead
		],
		# Client-side work is already under "waiting"; don't list it twice.
		"upcoming_tasks": [
			t
			for t in open_tasks
			if t.get("responsibility") not in CLIENT_SIDE
			and t.get("end_date")
			and today <= t["end_date"] <= ahead
		],
	}


def has_news(s: dict) -> bool:
	"""Anything worth an email? Open tickets alone are not: they have their
	own notifications, and a dormant project shouldn't mail every week."""
	return any(s.values())


def render(project_label, s, tickets, progress, today, links, fmt=str) -> str:
	"""The email body. Everything interpolated is escaped - ticket subjects
	are written by customers."""
	e = lambda v: html.escape(str(v or ""))  # noqa: E731

	def due(row, field):
		value = row.get(field)
		if not value:
			return ""
		late = value < today
		color = "#b91c1c" if late else "#6b7280"
		label = "overdue since" if late else "due"
		return f' <span style="color:{color};font-size:12px">({label} {e(fmt(value))})</span>'

	def block(title, items, accent=None):
		if not items:
			return ""
		style = (
			f"border-left:4px solid {accent};background:#fffbeb;padding:12px 16px;"
			if accent
			else "padding:4px 0;"
		)
		rows = "".join(f'<li style="margin:4px 0">{item}</li>' for item in items)
		return (
			f'<div style="{style}margin:0 0 18px;border-radius:6px">'
			f'<h3 style="margin:0 0 6px;font-size:15px">{e(title)}</h3>'
			f'<ul style="margin:0;padding-left:18px">{rows}</ul></div>'
		)

	waiting = (
		[e(t["subject"]) + due(t, "end_date") for t in s["waiting"]]
		+ [f"Sign off milestone: {e(m['title'])}" for m in s["signoffs"]]
		+ [f"Review task: {e(t['subject'])}" for t in s["reviews"]]
	)
	done = [f"Milestone completed: <b>{e(m['title'])}</b>" for m in s["done_milestones"]] + [
		e(t["subject"]) for t in s["done_tasks"]
	]
	upcoming = [
		f"Milestone: <b>{e(m['title'])}</b>" + due(m, "due_date") for m in s["upcoming_milestones"]
	] + [e(t["subject"]) + due(t, "end_date") for t in s["upcoming_tasks"]]
	ticket_rows = [
		f'<a href="{e(links["ticket"](t["name"]))}" style="color:#2563eb">#{e(t["name"])}</a> '
		f'{e(t["subject"])} <span style="color:#6b7280;font-size:12px">({e(t["status"])})</span>'
		for t in tickets
	]
	progress = max(0, min(100, cint(progress)))
	return (
		'<div style="font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:620px">'
		f'<h2 style="margin:0 0 4px;font-size:20px">{e(project_label)}</h2>'
		f'<p style="margin:0 0 10px;color:#6b7280">Weekly update · {e(fmt(today))} · '
		f"{progress}% complete</p>"
		'<div style="background:#e5e7eb;border-radius:6px;height:8px;margin:0 0 22px">'
		f'<div style="background:#2563eb;height:8px;border-radius:6px;width:{progress}%"></div></div>'
		+ block("Waiting on you", waiting, accent="#f59e0b")
		+ block("Done this week", done)
		+ block("Coming up", upcoming)
		+ block("Your open tickets", ticket_rows)
		+ f'<p style="margin:22px 0"><a href="{e(links["project"])}" style="display:inline-block;'
		"background:#2563eb;color:#ffffff;padding:10px 20px;border-radius:6px;"
		'text-decoration:none;font-weight:600">Open your project</a></p>'
		'<p style="color:#9ca3af;font-size:12px;margin:0">'
		"You receive this weekly update for this project. Reply to this email "
		"if you have a question.</p></div>"
	)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _d(value):
	return getdate(value) if value else None


def project_data(p) -> dict:
	"""Everything the email needs, limited to what the client sees in the
	portal: customer-visible milestones, non-internal tasks."""
	today = getdate()
	milestones = frappe.get_all(
		"HD Milestone",
		filters={"project": p.name, "customer_visible": 1},
		fields=["name", "title", "status", "due_date", "completed_on", "signoff_status"],
		order_by="sequence asc, due_date asc",
	)
	visible = [m.name for m in milestones]
	or_filters = [["project", "=", p.name]]
	if visible:
		or_filters.append(["milestone", "in", visible])
	tasks = frappe.get_all(
		"HD Addon Task",
		filters={"is_internal": 0},
		or_filters=or_filters,
		fields=["name", "subject", "status", "responsibility", "end_date", "completed_on", "customer_review"],
		order_by="end_date asc",
	)
	for m in milestones:
		m.due_date, m.completed_on = _d(m.due_date), _d(m.completed_on)
	for t in tasks:
		t.end_date, t.completed_on = _d(t.end_date), _d(t.completed_on)
	return {
		"today": today,
		"sections": sections(
			milestones, tasks, today, add_days(today, -WINDOW_DAYS), add_days(today, AHEAD_DAYS)
		),
		"tickets": _client_tickets(p),
		"progress": _client_progress(p, tasks),
	}


def _client_tickets(p) -> list:
	"""Open tickets for this project. A ticket with no project counts too, but
	only when the client has a single project - otherwise each project's email
	would repeat the same tickets."""
	if not p.customer:
		return []
	single = (
		frappe.db.count(
			"HD Project",
			{"customer": p.customer, "status": ["in", OPEN_PROJECT_STATUSES], "weekly_update": 1},
		)
		<= 1
	)
	or_filters = [["project", "=", p.name]]
	if single:
		or_filters.append(["project", "is", "not set"])
	return frappe.get_all(
		"HD Ticket",
		filters={"customer": p.customer, "status_category": ["!=", "Resolved"]},
		or_filters=or_filters,
		fields=["name", "subject", "status"],
		order_by="modified desc",
		limit_page_length=8,
	)


def _client_progress(p, tasks) -> int:
	"""Progress as the client sees it in the portal: over the tasks they can
	see, counting only their visible subtasks - the project rollup's rule."""
	from helpdesk.api.project import _task_completion

	if not tasks:
		return cint(p.progress)
	subs: dict = {}
	for s in frappe.get_all(
		"HD Task Subtask",
		filters={"task": ["in", [t.name for t in tasks]], "customer_visible": 1},
		fields=["task", "status"],
	):
		bucket = subs.setdefault(s.task, [0, 0])
		bucket[0] += 1
		bucket[1] += s.status == "Done"
	total = sum(
		_task_completion(t.status, subs.get(t.name, [0, 0])[1], subs.get(t.name, [0, 0])[0])
		for t in tasks
	)
	return round(total / len(tasks) * 100)


def recipients_for(p) -> list:
	"""The project's own list if it has one, else the client's primary
	contact(s). No primary contact means no email - never every contact."""
	explicit = [e for e in parse_recipients(p.get("weekly_update_recipients")) if validate_email_address(e)]
	if explicit or not p.customer:
		return explicit
	contacts = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": "HD Customer", "link_name": p.customer, "parenttype": "Contact"},
		pluck="parent",
	)
	if not contacts:
		return []
	return frappe.get_all(
		"Contact",
		filters={"name": ["in", contacts], "is_primary_contact": 1, "email_id": ["is", "set"]},
		pluck="email_id",
	)


def _links(p) -> dict:
	base = get_url()
	return {
		"project": f"{base}/helpdesk/my-projects/{p.name}",
		"ticket": lambda name: f"{base}/helpdesk/my-tickets/{name}",
	}


def _render(p, data) -> str:
	return render(
		p.project_name or p.name,
		data["sections"],
		data["tickets"],
		data["progress"],
		data["today"],
		_links(p),
		fmt=formatdate,
	)


def _send(p, data, recipients) -> None:
	sender = frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")
	frappe.sendmail(
		recipients=recipients,
		sender=sender,
		subject=_("{0}: weekly update").format(p.project_name or p.name),
		message=_render(p, data),
		reference_doctype="HD Project",
		reference_name=p.name,
		now=True,
	)
	frappe.db.set_value(
		"HD Project", p.name, "last_weekly_update_on", now_datetime(), update_modified=False
	)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def send_weekly_updates() -> None:
	"""Scheduler, Mondays 07:00 site time."""
	if not cint(frappe.db.get_single_value("HD Settings", "send_weekly_client_update")):
		return
	guard = add_days(now_datetime(), -RESEND_GUARD_DAYS)
	for name in frappe.get_all(
		"HD Project",
		filters={
			"status": ["in", OPEN_PROJECT_STATUSES],
			"weekly_update": 1,
			"customer": ["is", "set"],
		},
		pluck="name",
	):
		try:
			p = frappe.get_doc("HD Project", name)
			if p.last_weekly_update_on and get_datetime(p.last_weekly_update_on) > guard:
				continue
			data = project_data(p)
			recipients = recipients_for(p)
			if has_news(data["sections"]) and recipients:
				_send(p, data, recipients)
				frappe.db.commit()
		except Exception:
			frappe.log_error(title=f"Weekly client update failed for {name}")


# ---------------------------------------------------------------------------
# Agent API - anyone who may work on the project
# ---------------------------------------------------------------------------


def _assert_access(project: str) -> None:
	from helpdesk.api.project import _assert_agent_project

	_assert_agent_project(project)


@frappe.whitelist()
def get_client_update(project: str) -> dict:
	_assert_access(project)
	p = frappe.get_doc("HD Project", project)
	data = project_data(p)
	news = has_news(data["sections"])
	return {
		"enabled_globally": cint(
			frappe.db.get_single_value("HD Settings", "send_weekly_client_update")
		),
		"weekly_update": cint(p.get("weekly_update")),
		"recipients_text": p.get("weekly_update_recipients") or "",
		"recipients": recipients_for(p),
		"uses_primary_contact": not parse_recipients(p.get("weekly_update_recipients")),
		"last_sent": p.get("last_weekly_update_on"),
		"has_news": news,
		"html": _render(p, data) if news else None,
	}


@frappe.whitelist()
def save_client_update_settings(project: str, weekly_update, recipients_text: str = "") -> dict:
	_assert_access(project)
	emails = parse_recipients(recipients_text)
	bad = [e for e in emails if not validate_email_address(e)]
	if bad:
		frappe.throw(_("These aren't valid email addresses: {0}").format(", ".join(bad)))
	frappe.db.set_value(
		"HD Project",
		project,
		{
			"weekly_update": 1 if cint(weekly_update) else 0,
			"weekly_update_recipients": ", ".join(emails) or None,
		},
	)
	return get_client_update(project)


@frappe.whitelist()
def send_client_update_now(project: str) -> dict:
	"""Send this project's update now - works even while the weekly switch is
	off, so it can be checked on a real client before turning it on."""
	_assert_access(project)
	p = frappe.get_doc("HD Project", project)
	data = project_data(p)
	if not has_news(data["sections"]):
		frappe.throw(_("There is nothing to report on this project this week."))
	recipients = recipients_for(p)
	if not recipients:
		frappe.throw(
			_("No one to send it to. Add a recipient, or mark one of the client's contacts as primary.")
		)
	_send(p, data, recipients)
	return {"sent_to": recipients}
