# Post helpdesk activity to Pumble channels through incoming webhooks.
#
# Each HD Pumble Channel holds one channel's webhook URL, the events it wants
# and an optional scope (one project, one client, one inbox). Nothing is sent
# inline: notify() queues a background job that runs after the request
# commits, so Pumble being slow or down can never slow a ticket save. Every
# attempt lands in HD Pumble Log, which is also what makes SLA-breach alerts
# go out exactly once - surviving restarts and cache clears.
#
# Pumble's incoming-webhook contract: POST JSON {"text": ...} with markdown,
# at most 10,000 characters, one message per second per webhook.
# https://pumble.com/help/integrations/add-pumble-apps/incoming-webhooks-for-pumble/

import re
import time

import frappe
import requests
from frappe.utils import add_to_date, format_datetime, get_url, now_datetime, strip_html

WEBHOOK_PREFIX = "https://api.pumble.com/"
MAX_CHARS = 10000

# event -> the HD Pumble Channel checkbox that opts a channel into it
EVENT_FIELDS = {
	"new_ticket": "on_new_ticket",
	"customer_reply": "on_customer_reply",
	"sla_breach": "on_sla_breach",
	"ticket_resolved": "on_ticket_resolved",
	"project_activity": "on_project_activity",
}

# Where an email reply's quoted history begins.
_QUOTE_START = re.compile(
	r"\bOn\b.{0,120}?\bwrote:|-{2,}\s*Original Message\s*-{2,}|_{8,}|\bFrom:\s",
	re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Plumbing
# ---------------------------------------------------------------------------


def valid_webhook(url) -> bool:
	"""Only Pumble's own API host. A manager sets the URL, but it is this server
	that calls it, so it must never be able to point anywhere else."""
	return isinstance(url, str) and url.startswith(WEBHOOK_PREFIX) and not re.search(r"\s", url)


def safe(text, limit: int = 200) -> str:
	"""Customer-written text, defused for an internal team channel: one line,
	no @channel / @here / <<@user>> pings, no <url|text> or [text](url) links,
	no markdown that restyles the message. Customers reach the helpdesk from
	outside; they must not be able to ping or link-bait the team through it."""
	text = strip_html(str(text or ""))
	text = re.sub(r"\s+", " ", text).strip()
	for bad, good in (
		("@", "@​"),  # a zero-width space breaks @channel, @here and mentions
		("<", "‹"),
		(">", "›"),
		("[", "("),
		("]", ")"),
		("*", "∗"),
		("`", "'"),
		("~", "∼"),
	):
		text = text.replace(bad, good)
	if len(text) > limit:
		text = text[: limit - 1].rstrip() + "…"
	return text


def reply_text(content, limit: int = 280) -> str:
	"""The new part of an email reply, without the quoted thread under it."""
	text = re.sub(r"\s+", " ", strip_html(str(content or ""))).strip()
	match = _QUOTE_START.search(text)
	if match and match.start() > 0:
		text = text[: match.start()]
	return safe(text, limit)


def link(label: str, path: str) -> str:
	return f"[{label}]({get_url()}{path})"


def channels_for(event, project=None, customer=None, email_account=None) -> list:
	"""Enabled channels that want `event` and whose scope matches. An empty
	scope field means "any"."""
	try:
		rows = frappe.get_all(
			"HD Pumble Channel",
			filters={"enabled": 1, EVENT_FIELDS[event]: 1},
			fields=["name", "project", "customer", "email_account"],
		)
	except Exception:
		# Table may not exist yet (pre-migrate).
		return []
	return [
		r.name
		for r in rows
		if (not r.project or r.project == project)
		and (not r.customer or r.customer == customer)
		and (not r.email_account or r.email_account == email_account)
	]


def notify(
	event, text, *, project=None, customer=None, email_account=None, reference=None, event_key=None
) -> None:
	"""Queue `text` for every channel that wants this event in this scope.
	Safe to call from anywhere: sends nothing inline and never raises."""
	try:
		for channel in channels_for(event, project, customer, email_account):
			frappe.enqueue(
				"helpdesk.integrations.pumble.deliver",
				queue="short",
				enqueue_after_commit=True,
				channel=channel,
				event=event,
				text=text,
				reference=reference,
				event_key=event_key,
			)
	except Exception:
		frappe.log_error(title=f"Pumble: could not queue {event}")


def post(url: str, text: str) -> str | None:
	"""POST one message. None on success, otherwise a readable error. Retries
	once on 429 - Pumble allows one message per second per webhook."""
	payload = {"text": text[:MAX_CHARS]}
	for attempt in range(2):
		try:
			response = requests.post(url, json=payload, timeout=10)
		except requests.RequestException as e:
			return f"Could not reach Pumble: {e}"
		if response.status_code == 429 and attempt == 0:
			time.sleep(1.5)
			continue
		if 200 <= response.status_code < 300:
			return None
		return f"Pumble answered {response.status_code}: {response.text[:300]}"
	return "Pumble is rate-limiting this webhook (429)"


def deliver(channel, event, text, reference=None, event_key=None) -> None:
	"""Background job: send one message to one channel and log the outcome.
	Sends to the same channel are serialised a second apart, so a burst (a bulk
	update, several breaches at once) stays inside Pumble's limit."""
	if event_key and frappe.db.exists(
		"HD Pumble Log", {"channel": channel, "event_key": event_key, "status": "Sent"}
	):
		return
	if not frappe.db.exists("HD Pumble Channel", channel):
		return  # removed since the event was queued
	url = frappe.get_doc("HD Pumble Channel", channel).get_password(
		"webhook_url", raise_exception=False
	)
	if not valid_webhook(url):
		log_delivery(
			channel, event, text, "No valid Pumble webhook URL on this channel", reference, event_key
		)
		return

	lock = None
	try:
		lock = frappe.cache().lock(
			f"hd_pumble:{frappe.local.site}:{channel}", timeout=30, blocking_timeout=60
		)
		if not lock.acquire():
			lock = None
	except Exception:
		lock = None  # no lock available: send anyway, a 429 is retried
	try:
		error = post(url, text)
		if lock:
			time.sleep(1.05)  # keep the channel held for Pumble's 1/sec limit
	finally:
		if lock:
			try:
				lock.release()
			except Exception:
				pass
	log_delivery(channel, event, text, error, reference, event_key)


def log_delivery(channel, event, text, error, reference=None, event_key=None) -> None:
	ref_doctype, ref_name = (list(reference or []) + [None, None])[:2]
	frappe.get_doc(
		{
			"doctype": "HD Pumble Log",
			"channel": channel,
			"event": event,
			"event_key": event_key,
			"status": "Failed" if error else "Sent",
			"error": (error or "")[:1000] or None,
			"message": (text or "")[:1000],
			"reference_doctype": ref_doctype,
			"reference_name": ref_name,
		}
	).insert(ignore_permissions=True)


def prune_log() -> None:
	"""Daily: keep 60 days of delivery history."""
	try:
		frappe.db.delete(
			"HD Pumble Log", {"creation": ["<", add_to_date(now_datetime(), days=-60)]}
		)
	except Exception:
		pass  # table may not exist yet (pre-migrate)


def test_message() -> str:
	return (
		":wave: **Test from the helpdesk**: this channel is connected.\n"
		f"{link('Open the helpdesk', '/helpdesk')}"
	)


# ---------------------------------------------------------------------------
# Events. Each builds its message and calls notify(); none of them raises,
# because a chat notification must never break the action that caused it.
# ---------------------------------------------------------------------------


def _ticket_path(name) -> str:
	return f"/helpdesk/tickets/{name}"


def _who(ticket) -> str:
	who = safe(ticket.get("contact") or ticket.get("raised_by") or "Unknown", 80)
	if ticket.get("customer"):
		who += f" ({safe(ticket.customer, 80)})"
	return who


def _scope(ticket) -> dict:
	return {
		"project": ticket.get("project"),
		"customer": ticket.get("customer"),
		"email_account": ticket.get("email_account"),
	}


def ticket_created(ticket) -> None:
	try:
		if frappe.flags.initial_sync or ticket.subject == "Welcome to Helpdesk":
			return
		details = [f"From {_who(ticket)}", f"Priority {safe(ticket.priority or '-', 30)}"]
		if ticket.get("project"):
			label = frappe.db.get_value("HD Project", ticket.project, "project_name")
			details.append(f"Project {safe(label or ticket.project, 80)}")
		text = (
			f":ticket: **New ticket #{ticket.name}**: {safe(ticket.subject)}\n"
			+ " · ".join(details)
			+ "\n"
			+ link("Open ticket", _ticket_path(ticket.name))
		)
		notify("new_ticket", text, reference=["HD Ticket", ticket.name], **_scope(ticket))
	except Exception:
		frappe.log_error(title=f"Pumble: new-ticket message failed for {ticket.name}")


def customer_replied(ticket, communication) -> None:
	"""A customer wrote back on an existing ticket, by portal or email. The
	ticket's opening message is skipped: "New ticket" already covers it."""
	try:
		earlier = frappe.db.count(
			"Communication",
			{
				"reference_doctype": "HD Ticket",
				"reference_name": ticket.name,
				"sent_or_received": "Received",
				"name": ["!=", communication.name],
			},
		)
		if not earlier:
			return
		snippet = reply_text(communication.content)
		text = (
			f":speech_balloon: **{_who(ticket)} replied** on #{ticket.name}: {safe(ticket.subject)}\n"
			+ (f"*{snippet}*\n" if snippet else "")
			+ link("Open ticket", _ticket_path(ticket.name))
		)
		notify(
			"customer_reply",
			text,
			reference=["HD Ticket", ticket.name],
			event_key=f"reply:{communication.name}",
			**_scope(ticket),
		)
	except Exception:
		frappe.log_error(title=f"Pumble: reply message failed for {ticket.name}")


def ticket_resolved(ticket) -> None:
	try:
		text = (
			f":white_check_mark: **Resolved #{ticket.name}**: {safe(ticket.subject)}\n"
			+ link("Open ticket", _ticket_path(ticket.name))
		)
		notify("ticket_resolved", text, reference=["HD Ticket", ticket.name], **_scope(ticket))
	except Exception:
		frappe.log_error(title=f"Pumble: resolved message failed for {ticket.name}")


def sla_breach_sweep() -> None:
	"""Scheduler, every 5 minutes: announce each SLA deadline missed in the last
	day, once. HD Pumble Log's event_key keeps "once" true across restarts and
	cache clears; the one-day window stops a newly added channel from replaying
	every breach in history."""
	try:
		if not frappe.get_all(
			"HD Pumble Channel", filters={"enabled": 1, "on_sla_breach": 1}, limit_page_length=1
		):
			return
	except Exception:
		return  # table may not exist yet (pre-migrate)
	now = now_datetime()
	since = add_to_date(now, days=-1)
	checks = (
		(
			"response",
			"First response",
			"response_by",
			{"first_responded_on": ["is", "not set"], "agreement_status": "First Response Due"},
		),
		("resolution", "Resolution", "resolution_by", {"resolution_date": ["is", "not set"]}),
	)
	for kind, label, field, extra in checks:
		rows = frappe.get_all(
			"HD Ticket",
			filters={
				field: ["between", [since, now]],
				# Waiting on the customer pauses the clock; resolved has none left.
				"status_category": ["not in", ["Resolved", "Paused"]],
				**extra,
			},
			fields=[
				"name", "subject", "project", "customer", "email_account",
				"contact", "raised_by", "_assign", field,
			],
		)
		for ticket in rows:
			try:
				_announce_breach(ticket, kind, label, ticket.get(field))
			except Exception:
				frappe.log_error(title=f"Pumble: SLA message failed for {ticket.name}")


def _announce_breach(ticket, kind, label, deadline) -> None:
	assigned = frappe.parse_json(ticket.get("_assign") or "[]") or []
	names = [frappe.db.get_value("HD Agent", a, "agent_name") or a for a in assigned]
	owners = ", ".join(safe(n, 60) for n in names) if names else "nobody"
	text = (
		f":rotating_light: **SLA breached**: {label.lower()} overdue on #{ticket.name}: "
		f"{safe(ticket.subject)}\n"
		f"Was due {format_datetime(deadline, 'd MMM, HH:mm')} · Assigned to {owners}\n"
		+ link("Open ticket", _ticket_path(ticket.name))
	)
	notify(
		"sla_breach",
		text,
		reference=["HD Ticket", ticket.name],
		# The deadline is part of the key: if the SLA is reset and missed again,
		# that is a new breach worth announcing.
		event_key=f"sla:{kind}:{ticket.name}:{deadline}",
		**_scope(ticket),
	)


def _task_scope(task) -> tuple:
	"""(project, customer, path) for a task, via its project, milestone or add-on."""
	project = task.get("project") or (
		frappe.db.get_value("HD Milestone", task.milestone, "project")
		if task.get("milestone")
		else None
	)
	if project:
		customer = frappe.db.get_value("HD Project", project, "customer")
		return project, customer, f"/helpdesk/projects/{project}"
	if task.get("addon"):
		customer = frappe.db.get_value("HD Addon", task.addon, "customer")
		return None, customer, f"/helpdesk/addons/{task.addon}"
	return None, None, "/helpdesk/tasks"


def customer_commented(task, content) -> None:
	try:
		project, customer, path = _task_scope(task)
		quote = safe(content, 280)
		text = (
			f":speech_balloon: **{safe(customer or 'The client', 80)} commented** on task "
			f"{safe(task.subject)}\n"
			+ (f"*{quote}*\n" if quote else "")
			+ link("Open", path)
		)
		notify(
			"project_activity", text, project=project, customer=customer,
			reference=["HD Addon Task", task.name],
		)
	except Exception:
		frappe.log_error(title=f"Pumble: comment message failed for {task.name}")


def customer_reviewed(task, rating, comment=None) -> None:
	try:
		project, customer, path = _task_scope(task)
		rating = max(0, min(5, int(rating or 0)))
		stars = "★" * rating + "☆" * (5 - rating)
		quote = safe(comment, 280)
		text = (
			f":star: **{safe(customer or 'The client', 80)} reviewed** task "
			f"{safe(task.subject)}: {stars}\n"
			+ (f"*{quote}*\n" if quote else "")
			+ link("Open", path)
		)
		notify(
			"project_activity", text, project=project, customer=customer,
			reference=["HD Addon Task", task.name],
		)
	except Exception:
		frappe.log_error(title=f"Pumble: review message failed for {task.name}")


def milestone_signed_off(milestone, approved, note=None) -> None:
	try:
		project = milestone.project
		customer = frappe.db.get_value("HD Project", project, "customer")
		head = (
			":white_check_mark: **Milestone approved**"
			if approved
			else ":warning: **Changes requested**"
		)
		quote = safe(note, 280)
		text = (
			f"{head} by {safe(customer or 'the client', 80)}: {safe(milestone.title)}\n"
			+ (f"*{quote}*\n" if quote else "")
			+ link("Open project", f"/helpdesk/projects/{project}")
		)
		notify(
			"project_activity", text, project=project, customer=customer,
			reference=["HD Milestone", milestone.name],
		)
	except Exception:
		frappe.log_error(title=f"Pumble: sign-off message failed for {milestone.name}")
