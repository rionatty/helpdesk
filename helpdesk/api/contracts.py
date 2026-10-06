# Copyright (c) 2026, rionatty and contributors
# Support contracts and the hours bank.
#
# A contract gives a client a number of support hours per period: monthly,
# quarterly, yearly, or over the whole term. Usage is the client's billable
# time in that period, read from HD Time Log. Hours typed on a ticket's
# subtasks arrive there on their own, dated the day they were entered (see
# sync_subtask_hours). Agents can also log time on a ticket directly, or, for
# work outside tickets such as a training call, on the contract.
#
# Agents see the balance on the Contracts page and on each ticket; the client
# sees it on their portal home. Managers are told, by email and in Pumble
# when that is set up, when a client crosses the contract's alert level and
# again at 100%: once per level per period.
#
# Usage is counted by client and date, not stored on the contract. So a
# contract created today counts the time logged before it, and a ticket moved
# to another client takes its hours with it. A client has at most one active
# contract on any day, so no hour is counted twice.
#
# Descriptions are shown to the client, like lines on an invoice.

import calendar
import html
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_url, getdate, nowdate

from helpdesk.utils import get_customer, is_agent, is_agent_manager

PERIODS = ("Monthly", "Quarterly", "Yearly", "Whole contract")
STATUSES = ("Active", "Expired", "Cancelled")
DEFAULT_ALERT = 80
MAX_HOURS_PER_ENTRY = 24
CONTRACT_FIELDS = [
	"name",
	"customer",
	"contract_name",
	"status",
	"period",
	"hours_per_period",
	"start_date",
	"end_date",
	"alert_at_percent",
	"notes",
]
EDITABLE = tuple(f for f in CONTRACT_FIELDS if f != "name")
LOG_FIELDS = [
	"name",
	"date",
	"hours",
	"billable",
	"description",
	"ticket",
	"subtask",
	"job_card",
	"logged_by",
]
# Alert keys ("<period start>:<level>") remembered per contract: two years of
# monthly periods is plenty to never repeat an alert.
KEEP_ALERT_KEYS = 48


# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def _add_years(d: date, n: int) -> date:
	try:
		return d.replace(year=d.year + n)
	except ValueError:  # 29 February, in a year without one
		return d.replace(year=d.year + n, day=28)


def period_window(period: str, start: date, end: date | None, on: date) -> tuple:
	"""(first day, last day, label) of the contract period that contains `on`.

	Monthly and quarterly periods follow the calendar. Yearly periods run from
	the anniversary of the start date. "Whole contract" is the full term, or
	up to `on` when the contract has no end date. The window is clipped to the
	contract's own dates."""
	if period == "Monthly":
		f = on.replace(day=1)
		t = f.replace(day=calendar.monthrange(f.year, f.month)[1])
		label = f.strftime("%B %Y")
	elif period == "Quarterly":
		first = (on.month - 1) // 3 * 3 + 1
		f = date(on.year, first, 1)
		t = date(on.year, first + 2, calendar.monthrange(on.year, first + 2)[1])
		label = f"Q{(first - 1) // 3 + 1} {on.year}"
	elif period == "Yearly":
		# Both ends come from the start date itself, so a 29 February start
		# leaves no day between one contract year and the next.
		k = on.year - start.year
		if _add_years(start, k) > on:
			k -= 1
		f = _add_years(start, k)
		t = _add_years(start, k + 1) - timedelta(days=1)
		label = f"{f:%d %b %Y} - {t:%d %b %Y}"
	else:
		f, t = start, end or on
		label = "Whole contract"
	f = max(f, start)
	if end:
		t = min(t, end)
	return f, t, label


def usage_of(included, used) -> dict:
	included, used = flt(included), flt(used)
	return {
		"included": round(included, 2),
		"used": round(used, 2),
		"remaining": round(included - used, 2),
		"pct": round(used / included * 100) if included > 0 else 0,
	}


def thresholds_crossed(before_used, after_used, included, alert_at) -> list:
	"""The alert levels, in %, that a change in usage crossed on the way up:
	the contract's own level and 100%."""
	included = flt(included)
	if included <= 0:
		return []
	levels = sorted({max(1, min(100, cint(alert_at) or DEFAULT_ALERT)), 100})
	before = round(flt(before_used) / included * 100, 6)
	after = round(flt(after_used) / included * 100, 6)
	return [level for level in levels if before < level <= after]


def contract_state(status: str, start: date, end: date | None, on: date) -> str:
	if status != "Active":
		return status
	if on < start:
		return "Not started"
	if end and on > end:
		return "Ended"
	return "In force"


def overlaps(a_start: date, a_end: date | None, b_start: date, b_end: date | None) -> bool:
	"""Whether two date ranges share a day. A missing end runs forever."""
	return (b_end is None or a_start <= b_end) and (a_end is None or b_start <= a_end)


def take_back(hours: list, amount: float) -> list:
	"""Take `amount` off a list of entries' hours, newest entry first, and
	return what each entry is left with (0 means delete it). Used when a
	subtask's hours go down: the correction comes off its latest entries,
	instead of showing as a negative line on the client's statement."""
	out = []
	amount = flt(amount)
	for h in hours:
		h = flt(h)
		cut = min(h, max(amount, 0))
		out.append(round(h - cut, 4))
		amount = round(amount - cut, 4)
	return out


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _billable_hours(customer, f: date, t: date) -> float:
	if not customer or f > t:
		return 0.0
	return sum(
		flt(h)
		for h in frappe.get_all(
			"HD Time Log",
			filters={"customer": customer, "billable": 1, "date": ["between", [f, t]]},
			pluck="hours",
		)
	)


def contract_usage(c, on=None) -> dict:
	"""Usage in the period of contract `c` (a document or a row) that holds
	`on`, today by default."""
	on = getdate(on or nowdate())
	start = getdate(c.start_date)
	end = getdate(c.end_date) if c.end_date else None
	f, t, label = period_window(c.period or "Monthly", start, end, on)
	return {
		**usage_of(c.hours_per_period, _billable_hours(c.customer, f, t)),
		"period_from": f,
		"period_to": t,
		"period_label": label,
		"alert_at": cint(c.alert_at_percent) or DEFAULT_ALERT,
		"state": contract_state(c.status, start, end, on),
	}


def active_contract(customer, on=None):
	"""The client's contract in force on `on` (today by default), or None."""
	if not customer:
		return None
	on = getdate(on or nowdate())
	for name, end in frappe.get_all(
		"HD Support Contract",
		filters={"customer": customer, "status": "Active", "start_date": ["<=", on]},
		fields=["name", "end_date"],
		order_by="start_date desc",
		as_list=True,
	):
		if not end or getdate(end) >= on:
			return frappe.get_doc("HD Support Contract", name)
	return None


def validate_contract(doc) -> None:
	"""HD Support Contract.validate - so the desk form keeps the same rules."""
	doc.contract_name = (doc.contract_name or "").strip()
	doc.status = doc.status or "Active"
	doc.period = doc.period or "Monthly"
	if not doc.customer:
		frappe.throw(_("Pick the client this contract is for"))
	if not doc.contract_name:
		frappe.throw(_("Give the contract a name"))
	if doc.period not in PERIODS:
		frappe.throw(_("Invalid period"))
	if doc.status not in STATUSES:
		frappe.throw(_("Invalid status"))
	if flt(doc.hours_per_period) <= 0:
		frappe.throw(_("Included hours must be more than zero"))
	if not doc.start_date:
		frappe.throw(_("Set the date the contract starts"))
	start = getdate(doc.start_date)
	end = getdate(doc.end_date) if doc.end_date else None
	if end and end < start:
		frappe.throw(_("The contract ends before it starts"))
	doc.alert_at_percent = max(1, min(100, cint(doc.alert_at_percent) or DEFAULT_ALERT))
	if doc.status != "Active":
		return
	for other in frappe.get_all(
		"HD Support Contract",
		filters={"customer": doc.customer, "status": "Active", "name": ["!=", doc.name or ""]},
		fields=["name", "contract_name", "start_date", "end_date"],
	):
		other_end = getdate(other.end_date) if other.end_date else None
		if overlaps(start, end, getdate(other.start_date), other_end):
			frappe.throw(
				_(
					"{0} already has an active contract for some of these dates ({1}). "
					"Give it an end date, or cancel it, first."
				).format(doc.customer, other.contract_name or other.name)
			)


def _record(customer, on, change) -> None:
	"""Run `change`, which writes time logs, then tell managers if that took
	the client's contract across an alert level."""
	c = active_contract(customer, on)
	before = contract_usage(c, on) if c else None
	change()
	if not c:
		return
	try:
		_check_alerts(c, before, contract_usage(c, on))
	except Exception:
		frappe.log_error(title=f"Support hours: alert failed for {c.name}")


def _new_log(
	customer, ticket, subtask, on, hours, description=None, billable=1, job_card=None, logged_by=None
) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "HD Time Log",
				"customer": customer,
				"ticket": ticket,
				"subtask": subtask,
				"job_card": job_card,
				"date": on,
				"hours": hours,
				"billable": 1 if cint(billable) else 0,
				"description": description or None,
				"logged_by": logged_by or frappe.session.user,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def sync_subtask_hours(subtask) -> None:
	"""Keep a ticket subtask's time logs adding up to its hours_spent; called
	on every save. More hours are logged today, onto this agent's entry for
	today when there is one. Fewer hours are taken back from the newest
	entries (see take_back)."""
	before = subtask.get_doc_before_save()
	old = flt(before.hours_spent) if before else 0.0
	new = flt(subtask.hours_spent)
	if abs(new - old) < 0.001:
		return
	customer = frappe.db.get_value("HD Ticket", subtask.ticket, "customer")
	today = getdate(nowdate())

	def change():
		if new > old:
			mine = frappe.db.get_value(
				"HD Time Log",
				{"subtask": subtask.name, "date": today, "logged_by": frappe.session.user},
				["name", "hours"],
				as_dict=True,
			)
			if mine:
				frappe.db.set_value(
					"HD Time Log", mine.name, "hours", round(flt(mine.hours) + new - old, 4)
				)
			else:
				_new_log(customer, subtask.ticket, subtask.name, today, round(new - old, 4))
			return
		entries = frappe.get_all(
			"HD Time Log",
			filters={"subtask": subtask.name},
			fields=["name", "hours"],
			order_by="date desc, creation desc",
		)
		for entry, left in zip(entries, take_back([e.hours for e in entries], old - new)):
			if left <= 0:
				frappe.delete_doc("HD Time Log", entry.name, ignore_permissions=True)
			elif left != flt(entry.hours):
				frappe.db.set_value("HD Time Log", entry.name, "hours", left)

	_record(customer, today, change)


def retag_ticket(ticket: str, customer) -> None:
	"""HD Ticket.on_update: a ticket moved to another client takes its time."""
	log = frappe.qb.DocType("HD Time Log")
	frappe.qb.update(log).set(log.customer, customer or None).where(log.ticket == ticket).run()


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def _check_alerts(c, before: dict, after: dict) -> None:
	crossed = thresholds_crossed(before["used"], after["used"], after["included"], after["alert_at"])
	if not crossed:
		return
	stored = frappe.db.get_value("HD Support Contract", c.name, "alerts_sent") or ""
	sent = [k for k in stored.split(",") if k]
	new = [level for level in crossed if f"{after['period_from']}:{level}" not in sent]
	if not new:
		return
	sent += [f"{after['period_from']}:{level}" for level in new]
	frappe.db.set_value(
		"HD Support Contract",
		c.name,
		"alerts_sent",
		",".join(sorted(sent)[-KEEP_ALERT_KEYS:]),
		update_modified=False,
	)
	_send_alert(c, after, max(new))


def alert_subject(customer: str, usage: dict) -> str:
	if usage["pct"] >= 100:
		return _("{0} has used all its support hours ({1}%)").format(customer, usage["pct"])
	return _("{0} has used {1}% of its support hours").format(customer, usage["pct"])


def alert_body(c, usage: dict, site_url: str) -> str:
	"""The managers' email. Every value is escaped: client and contract names
	are typed by people."""
	e = html.escape
	if usage["remaining"] >= 0:
		left = _("{0} h left").format(usage["remaining"])
	else:
		left = _("{0} h over").format(round(-usage["remaining"], 2))
	return (
		f"<p><b>{e(c.customer)}</b> has used <b>{usage['used']} of {usage['included']} hours</b> "
		f"({usage['pct']}%, {e(left)}) on <b>{e(c.contract_name or c.name)}</b> "
		f"for {e(usage['period_label'])}.</p>"
		f'<p><a href="{e(site_url)}/helpdesk/contracts">{e(_("Open contracts"))}</a></p>'
	)


def _send_alert(c, usage: dict, level: int) -> None:
	from helpdesk.integrations import pumble

	pumble.hours_alert(c, usage, level)
	managers = frappe.get_all(
		"Has Role", filters={"role": "Agent Manager", "parenttype": "User"}, pluck="parent"
	)
	recipients = (
		frappe.get_all(
			"User",
			filters={"name": ["in", managers], "enabled": 1, "user_type": "System User"},
			pluck="email",
		)
		if managers
		else []
	)
	if not recipients:
		return
	frappe.enqueue(
		"helpdesk.api.contracts.deliver_alert",
		queue="short",
		enqueue_after_commit=True,
		recipients=recipients,
		subject=alert_subject(c.customer, usage),
		message=alert_body(c, usage, get_url()),
		contract=c.name,
	)


def deliver_alert(recipients, subject, message, contract) -> None:
	"""Background job: same sender resolution as the other helpdesk emails."""
	sender = frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")
	frappe.sendmail(
		recipients=recipients,
		sender=sender,
		subject=subject,
		message=message,
		reference_doctype="HD Support Contract",
		reference_name=contract,
		now=True,
	)


# ---------------------------------------------------------------------------
# Agent API
# ---------------------------------------------------------------------------


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can do this"), frappe.PermissionError)


def _manager_only() -> None:
	frappe.only_for(["Agent Manager", "System Manager"])


def _assert_ticket(ticket: str) -> None:
	if not ticket or not frappe.db.exists("HD Ticket", ticket):
		frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
	if not frappe.has_permission("HD Ticket", "read", doc=ticket):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _can_change(log) -> bool:
	return is_agent_manager() or log.logged_by == frappe.session.user


def _subjects(doctype: str, names: set) -> dict:
	if not names:
		return {}
	return dict(
		frappe.get_all(
			doctype, filters={"name": ["in", list(names)]}, fields=["name", "subject"], as_list=True
		)
	)


def _describe(logs: list) -> None:
	"""Add display names, subtask and ticket subjects, and what the viewer may
	change, to time-log rows (agent views)."""
	users = {l.logged_by for l in logs if l.logged_by}
	names = (
		{
			u.name: u.full_name or u.name
			for u in frappe.get_all(
				"User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"]
			)
		}
		if users
		else {}
	)
	subtask_subjects = _subjects("HD Ticket Subtask", {l.subtask for l in logs if l.subtask})
	ticket_subjects = _subjects("HD Ticket", {l.ticket for l in logs if l.ticket})
	manager, me = is_agent_manager(), frappe.session.user
	for l in logs:
		l["logged_by_name"] = names.get(l.logged_by, l.logged_by)
		l["subtask_subject"] = subtask_subjects.get(l.subtask)
		l["ticket_subject"] = ticket_subjects.get(l.ticket)
		l["can_change"] = manager or l.logged_by == me
		# Subtask time follows the subtask's hours; it is changed there.
		l["can_delete"] = l["can_change"] and not l.subtask


@frappe.whitelist()
def list_contracts() -> list:
	_assert_agent()
	today = getdate(nowdate())
	rows = frappe.get_all(
		"HD Support Contract",
		fields=CONTRACT_FIELDS,
		order_by="customer asc, start_date desc",
		limit_page_length=0,
	)
	for r in rows:
		r.update(contract_usage(r, today))
	return rows


@frappe.whitelist()
def save_contract(data) -> str:
	_manager_only()
	data = frappe._dict(frappe.parse_json(data) if isinstance(data, str) else (data or {}))
	doc = (
		frappe.get_doc("HD Support Contract", data.name)
		if data.get("name")
		else frappe.new_doc("HD Support Contract")
	)
	for field in EDITABLE:
		if field in data:
			value = data.get(field)
			doc.set(field, None if value in ("", None) else value)
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def delete_contract(name: str) -> bool:
	"""Logged time belongs to the client, not the contract, so it stays."""
	_manager_only()
	frappe.delete_doc("HD Support Contract", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def log_time(
	hours: float,
	description: str | None = None,
	ticket: str | None = None,
	contract: str | None = None,
	day: str | None = None,
	billable: int = 1,
) -> bool:
	"""Log time by hand, on a ticket or, for work outside tickets, on a
	contract. Subtask hours log themselves (sync_subtask_hours)."""
	_assert_agent()
	hours = flt(hours)
	if hours <= 0 or hours > MAX_HOURS_PER_ENTRY:
		frappe.throw(_("Hours must be more than 0 and at most {0}").format(MAX_HOURS_PER_ENTRY))
	on = getdate(day or nowdate())
	if on > getdate(nowdate()):
		frappe.throw(_("Time can't be logged on a future date"))
	description = (description or "").strip()[:1000]
	if ticket:
		_assert_ticket(ticket)
		customer = frappe.db.get_value("HD Ticket", ticket, "customer")
	elif contract:
		customer = frappe.db.get_value("HD Support Contract", contract, "customer")
		if not customer:
			frappe.throw(_("Contract not found"), frappe.DoesNotExistError)
		if not description:
			frappe.throw(_("Say what the time was for: the client sees it on their statement"))
	else:
		frappe.throw(_("Log time on a ticket or on a contract"))

	def change():
		_new_log(customer, ticket, None, on, hours, description, billable)

	if cint(billable):
		_record(customer, on, change)
	else:
		change()
	return True


@frappe.whitelist()
def set_billable(name: str, billable: int) -> bool:
	_assert_agent()
	log = frappe.get_doc("HD Time Log", name)
	if not _can_change(log):
		frappe.throw(
			_("Only the person who logged this time, or a manager, can change it"),
			frappe.PermissionError,
		)
	if cint(billable) and not log.billable:
		_record(log.customer, log.date, lambda: log.db_set("billable", 1))
	else:
		log.db_set("billable", 1 if cint(billable) else 0)
	return True


@frappe.whitelist()
def delete_time_log(name: str) -> bool:
	_assert_agent()
	log = frappe.get_doc("HD Time Log", name)
	if log.subtask:
		frappe.throw(_("This time comes from a subtask. Change the subtask's hours instead."))
	if log.job_card and frappe.db.get_value("HD Job Card", log.job_card, "status") == "Signed":
		frappe.throw(_("This time is on job card {0}, which the client has signed").format(log.job_card))
	if not _can_change(log):
		frappe.throw(
			_("Only the person who logged this time, or a manager, can remove it"),
			frappe.PermissionError,
		)
	frappe.delete_doc("HD Time Log", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def get_ticket_time(ticket: str) -> dict:
	"""The ticket sidebar: this ticket's time, and the client's balance."""
	_assert_agent()
	_assert_ticket(ticket)
	customer = frappe.db.get_value("HD Ticket", ticket, "customer")
	logs = frappe.get_all(
		"HD Time Log",
		filters={"ticket": ticket},
		fields=LOG_FIELDS,
		order_by="date desc, creation desc",
	)
	_describe(logs)
	c = active_contract(customer)
	return {
		"customer": customer,
		"contract": c.name if c else None,
		"contract_name": c.contract_name if c else None,
		"usage": contract_usage(c) if c else None,
		"logs": logs,
		"total": round(sum(flt(l.hours) for l in logs), 2),
	}


@frappe.whitelist()
def get_statement(contract: str, on: str | None = None) -> dict:
	"""Every entry for the contract's client in the period holding `on`."""
	_assert_agent()
	c = frappe.get_doc("HD Support Contract", contract)
	u = contract_usage(c, on)
	logs = (
		frappe.get_all(
			"HD Time Log",
			filters={
				"customer": c.customer,
				"date": ["between", [u["period_from"], u["period_to"]]],
			},
			fields=LOG_FIELDS,
			order_by="date asc, creation asc",
			limit_page_length=0,
		)
		if u["period_from"] <= u["period_to"]
		else []
	)
	_describe(logs)
	start = getdate(c.start_date)
	end = getdate(c.end_date) if c.end_date else None
	paged = c.period != "Whole contract"
	return {
		**{f: c.get(f) for f in CONTRACT_FIELDS},
		**u,
		"logs": logs,
		"non_billable": round(sum(flt(l.hours) for l in logs if not l.billable), 2),
		"has_previous": paged and u["period_from"] > start,
		"has_next": paged
		and u["period_to"] < getdate(nowdate())
		and (end is None or u["period_to"] < end),
	}


# ---------------------------------------------------------------------------
# Customer portal
# ---------------------------------------------------------------------------


def client_line(description, subtask_subject, ticket) -> str:
	"""What a statement line says to the client."""
	if description:
		return description
	if subtask_subject:
		return subtask_subject
	return _("Ticket #{0}").format(ticket) if ticket else _("Support")


@frappe.whitelist()
def get_my_support_plans() -> list:
	"""The signed-in client's contracts in force, with this period's usage and
	its billable entries. Who logged an entry, internal notes and ticket
	subjects (the ticket may be a colleague's) are left out."""
	if is_agent():
		return []
	companies = get_customer(frappe.session.user)
	if not companies:
		return []
	today = getdate(nowdate())
	out = []
	for c in frappe.get_all(
		"HD Support Contract",
		filters={"customer": ["in", companies], "status": "Active"},
		fields=CONTRACT_FIELDS,
		order_by="start_date desc",
	):
		u = contract_usage(c, today)
		if u["state"] != "In force":
			continue
		entries = frappe.get_all(
			"HD Time Log",
			filters={
				"customer": c.customer,
				"billable": 1,
				"date": ["between", [u["period_from"], u["period_to"]]],
			},
			fields=["date", "hours", "description", "ticket", "subtask"],
			order_by="date desc, creation desc",
			limit_page_length=50,
		)
		subjects = _subjects("HD Ticket Subtask", {e.subtask for e in entries if e.subtask})
		out.append(
			{
				"name": c.name,
				"contract_name": c.contract_name,
				"customer": c.customer,
				"period": c.period,
				"end_date": c.end_date,
				**u,
				"entries": [
					{
						"date": e.date,
						"hours": e.hours,
						"ticket": e.ticket,
						"what": client_line(e.description, subjects.get(e.subtask), e.ticket),
					}
					for e in entries
				],
			}
		)
	return out
