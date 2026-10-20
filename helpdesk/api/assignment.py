# Copyright (c) 2026, rionatty and contributors
# Telling the customer who is handling their ticket, and by when.
#
# Assignment: frappe's assign-to makes one ToDo per assignee, whether from the
# assign dialog, auto-assignment, an assignment rule or a bulk action, so a
# ToDo hook catches them all (on_todo_insert). After the request commits, the
# customer hears which agent is handling the ticket. The exception is a
# ticket auto-assigned while it is being created: its acknowledgement names
# the agent, instead of a second email arriving right behind it.
#
# Expected resolution: the assigned agent (or a manager) says how long the
# ticket will take (set_resolution_eta). The customer sees it on the ticket
# and is told when it is set or moves.
#
# Both go out through HD Ticket.send_customer_notice: the acknowledgement's
# gates (automated senders, our own inboxes, customers who turned email
# updates off, the per-ticket loop breaker last, RFC 3834 headers), or on
# WhatsApp for a WhatsApp ticket. Settings > Email Notifications switches the
# notices off as a whole; the customer still sees both on the ticket.

import html
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, format_datetime, get_datetime, get_fullname, now_datetime

from helpdesk.utils import is_agent, is_agent_manager

MAX_HOURS = 24 * 366
MIN_LEAD = timedelta(minutes=5)

# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def round_up(dt: datetime, minutes: int = 15) -> datetime:
	"""To the next quarter hour: "by 12:15", not "by 12:07"."""
	dt = dt.replace(second=0, microsecond=0)
	extra = -dt.minute % minutes
	return dt + timedelta(minutes=extra)


def eta_from_hours(now: datetime, hours: float) -> datetime:
	return round_up(now + timedelta(hours=hours))


def first_name(full_name: str | None) -> str:
	return (full_name or "").strip().split(" ")[0]


def _greeting(name: str | None) -> str:
	return _("Hello {0},").format(name) if name else _("Hello,")


def assignment_message(agent, number, subject, eta_label, portal_url, customer_name=None):
	"""(html, text) of the notice that an agent is handling the ticket."""
	e = html.escape
	line = _("{0} is now handling your ticket #{1}: {2}.").format(agent, number, subject)
	eta_line = _("They expect to resolve it by {0}.").format(eta_label) if eta_label else ""
	follow = _("You will get their replies by email. You can also follow the ticket here:")
	html_body = (
		f"<p>{e(_greeting(customer_name))}</p><p>{e(line)}</p>"
		+ (f"<p>{e(eta_line)}</p>" if eta_line else "")
		+ f'<p>{e(follow)} <a href="{e(portal_url)}">{e(portal_url)}</a></p>'
	)
	text = " ".join(x for x in (line, eta_line) if x)
	return html_body, text


def eta_message(agent, number, subject, eta_label, old_label, portal_url, customer_name=None):
	"""(html, text) of the notice of a new or changed expected resolution."""
	e = html.escape
	if old_label:
		line = _("{0} now expects to resolve your ticket #{1}: {2} by {3} (it was {4}).").format(
			agent, number, subject, eta_label, old_label
		)
	else:
		line = _("{0} expects to resolve your ticket #{1}: {2} by {3}.").format(
			agent, number, subject, eta_label
		)
	follow = _("You can follow the ticket here:")
	html_body = (
		f"<p>{e(_greeting(customer_name))}</p><p>{e(line)}</p>"
		f'<p>{e(follow)} <a href="{e(portal_url)}">{e(portal_url)}</a></p>'
	)
	return html_body, line


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def enabled() -> bool:
	"""Settings > Email Notifications > Assignment and expected resolution."""
	return bool(cint(frappe.db.get_single_value("HD Settings", "notify_customer_of_assignment")))


def agent_name(user: str | None) -> str:
	if not user:
		return _("Our team")
	return frappe.db.get_value("HD Agent", user, "agent_name") or get_fullname(user) or user


def assignees(ticket_name: str) -> list:
	try:
		value = frappe.parse_json(frappe.db.get_value("HD Ticket", ticket_name, "_assign") or "[]")
	except Exception:
		return []
	return value if isinstance(value, list) else []


def eta_label(value) -> str | None:
	return format_datetime(value, "EEE d MMM, HH:mm") if value else None


def _customer_first_name(ticket) -> str:
	if ticket.contact:
		name = frappe.db.get_value("Contact", ticket.contact, ["first_name", "full_name"], as_dict=True)
		if name:
			return first_name(name.first_name or name.full_name)
	return ""


def _log(ticket: str, action: str) -> None:
	try:
		from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import log_ticket_activity

		log_ticket_activity(ticket, action)
	except Exception:
		pass


def handled_by_html(ticket) -> str:
	"""A line for the acknowledgement of a ticket assigned as it was created."""
	text = handled_by_text(ticket)
	return f"<p>{html.escape(text)}</p>" if text else ""


def handled_by_text(ticket) -> str:
	if not enabled():
		return ""
	agents = assignees(ticket.name)
	return _("{0} is handling your ticket.").format(agent_name(agents[0])) if agents else ""


def _acknowledgement_names_agent(ticket: str) -> bool:
	"""The ticket is being created in this same request, and its
	acknowledgement (sent once it commits) will name the agent."""
	if frappe.flags.get("hd_new_ticket") != ticket:
		return False
	if frappe.db.get_value("HD Ticket", ticket, "whatsapp_number"):
		return bool(cint(frappe.db.get_single_value("HD WhatsApp Settings", "send_acknowledgement")))
	return bool(cint(frappe.db.get_single_value("HD Settings", "send_acknowledgement_email")))


# ---------------------------------------------------------------------------
# Hooks and background jobs
# ---------------------------------------------------------------------------


def on_todo_insert(doc, method=None) -> None:
	"""ToDo.after_insert: a new assignment. Never breaks the assignment."""
	if doc.reference_type != "HD Ticket" or doc.status != "Open" or not doc.allocated_to:
		return
	try:
		if not enabled() or not frappe.db.exists("HD Agent", doc.allocated_to):
			return
		if _acknowledgement_names_agent(doc.reference_name):
			return
		frappe.enqueue(
			"helpdesk.api.assignment.notify_assignment",
			queue="short",
			enqueue_after_commit=True,
			ticket=doc.reference_name,
			agent=doc.allocated_to,
		)
	except Exception:
		frappe.log_error(title=f"Assignment notice: could not queue for {doc.reference_name}")


def notify_assignment(ticket: str, agent: str) -> None:
	"""Background job: tell the customer who is handling their ticket."""
	if not frappe.db.exists("HD Ticket", ticket):
		return
	t = frappe.get_doc("HD Ticket", ticket)
	if t.status_category == "Resolved" or agent not in assignees(ticket):
		return  # resolved, or unassigned again before this ran
	name = agent_name(agent)
	eta = t.resolution_eta if t.resolution_eta and get_datetime(t.resolution_eta) > now_datetime() else None
	body, text = assignment_message(
		name, t.name, t.subject, eta_label(eta), t.portal_uri, _customer_first_name(t)
	)
	outcome = t.send_customer_notice(
		"assignment", _("Ticket #{0}: {1} is handling your request").format(t.name, name), body, text
	)
	if outcome == "sent":
		_log(t.name, f"told the customer that {name} is handling it")


def notify_eta(ticket: str, old: str | None = None, by: str | None = None) -> None:
	"""Background job: tell the customer the expected resolution."""
	if not frappe.db.exists("HD Ticket", ticket):
		return
	t = frappe.get_doc("HD Ticket", ticket)
	if not t.resolution_eta or t.status_category == "Resolved":
		return
	agents = assignees(ticket)
	who = agent_name(agents[0] if agents else by)
	label = eta_label(t.resolution_eta)
	body, text = eta_message(who, t.name, t.subject, label, old, t.portal_uri, _customer_first_name(t))
	outcome = t.send_customer_notice(
		"eta", _("Ticket #{0}: expected resolution {1}").format(t.name, label), body, text
	)
	if outcome == "sent":
		_log(t.name, f"told the customer the expected resolution ({label})")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def set_resolution_eta(
	ticket: str, hours: float | None = None, eta: str | None = None, notify: int = 1
) -> dict:
	"""Set how long the ticket will take: `hours` from now, or an exact
	`eta`; neither clears it. The ticket's assigned agents and managers."""
	if not is_agent():
		frappe.throw(_("Only agents can do this"), frappe.PermissionError)
	if not frappe.db.exists("HD Ticket", ticket):
		frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
	me = frappe.session.user
	if me not in assignees(ticket) and not is_agent_manager():
		frappe.throw(
			_("Only the agent assigned to this ticket, or a manager, can set when it will be resolved"),
			frappe.PermissionError,
		)
	t = frappe.get_doc("HD Ticket", ticket)
	old = t.resolution_eta
	now = now_datetime()
	if hours not in (None, "") and flt(hours) > 0:
		if flt(hours) > MAX_HOURS:
			frappe.throw(_("Pick a time within the next year"))
		new = eta_from_hours(now, flt(hours))
	elif eta:
		new = get_datetime(eta).replace(second=0, microsecond=0)
		if new < now + MIN_LEAD:
			frappe.throw(_("Pick a time in the future"))
		if new > now + timedelta(hours=MAX_HOURS):
			frappe.throw(_("Pick a time within the next year"))
	else:
		new = None
	# db_set: no ticket hooks (SLA, status emails) for this one field.
	t.db_set("resolution_eta", new, notify=True)
	label = eta_label(new)
	_log(t.name, f"set the expected resolution to {label}" if new else "cleared the expected resolution")
	told = False
	if new and cint(notify) and enabled() and t.status_category != "Resolved":
		frappe.enqueue(
			"helpdesk.api.assignment.notify_eta",
			queue="short",
			enqueue_after_commit=True,
			ticket=t.name,
			old=eta_label(old) if old and get_datetime(old) > now else None,
			by=me,
		)
		told = True
	return {"resolution_eta": new, "label": label, "customer_told": told}
