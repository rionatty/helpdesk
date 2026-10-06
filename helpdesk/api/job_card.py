# Copyright (c) 2026, rionatty and contributors
# Job cards: the printable record of a piece of work done for a client.
#
# An agent opens a card from a ticket, or for a client directly. The card
# says what was asked, what was done, what is recommended next and how long
# it took, and lists any items used. A card opened from a ticket starts with
# that ticket's logged time that is not on a card yet. Lines typed on the card
# are logged as time too (unless the agent says not to), so they count in the
# client's support hours exactly once. HD Time Log.job_card stops the same
# time landing on two cards.
#
# The card's lines are a copy, not a live view: a printed or signed card keeps
# saying what the client was shown even if the time ledger is corrected later.
#
# Sign-off: the client signs on the agent's screen or in the portal (cards
# marked Completed), or the agent records that a paper copy was signed. A
# signed card is locked; only a manager can cancel it.

import html
import re

import frappe
from frappe import _
from frappe.utils import (
	cint,
	flt,
	format_date,
	format_datetime,
	get_fullname,
	get_url,
	getdate,
	now_datetime,
	nowdate,
	strip_html,
	to_timedelta,
)
from werkzeug.wrappers import Response

from helpdesk.api import contracts
from helpdesk.utils import get_customer, is_agent, is_agent_manager

STATUSES = ("Open", "Completed", "Signed", "Cancelled")
SERVICE_TYPES = ("Remote", "On-site", "Phone")
WORK_STATUSES = ("Resolved", "Partly resolved", "Follow-up needed")
EDITABLE = (
	"date",
	"customer",
	"ticket",
	"project",
	"service_type",
	"location",
	"time_in",
	"time_out",
	"technician",
	"contact",
	"contact_name",
	"contact_phone",
	"contact_email",
	"work_requested",
	"work_done",
	"work_status",
	"recommendations",
)
CARD_FIELDS = [
	"name",
	"status",
	*EDITABLE,
	"technician_name",
	"total_hours",
	"signed_by",
	"signed_designation",
	"signed_on",
	"satisfied",
	"customer_comments",
	"customer_signature",
	"creation",
]
LINE_FIELDS = ("date", "hours", "description", "technician", "technician_name", "time_log", "from_card")
MAX_LINES = 100
# A drawn signature, as the signature pad exports it - nothing else.
SIGNATURE = re.compile(r"^data:image/png;base64,[A-Za-z0-9+/]+={0,2}$")
MAX_SIGNATURE_CHARS = 500_000


# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def total_hours(lines) -> float:
	return round(sum(flt(l.get("hours")) for l in lines), 2)


def valid_signature(data) -> bool:
	return isinstance(data, str) and len(data) <= MAX_SIGNATURE_CHARS and bool(SIGNATURE.match(data))


def plan_lines(old: list, incoming: list, log_time: bool) -> dict:
	"""What saving a card's lines does to the time ledger.

	`old` and `incoming` are line dicts; a line's `time_log` is the time log
	behind it, and `from_card` says the card created that log. Returns:
	  update - logs the card created, to be given the line's new values
	  link   - existing logs (e.g. the ticket's) now on the card
	  create - indexes of incoming lines that need a new log
	  delete - logs the card created whose line was removed
	  unlink - other logs whose line was removed: they stay, off the card
	"""
	plan = {"update": [], "link": [], "create": [], "delete": [], "unlink": []}
	kept = set()
	for i, line in enumerate(incoming):
		log = line.get("time_log")
		if log:
			kept.add(log)
			if cint(line.get("from_card")):
				plan["update"].append(log)
			else:
				plan["link"].append(log)
		elif log_time:
			plan["create"].append(i)
	for line in old:
		log = line.get("time_log")
		if log and log not in kept:
			plan["delete" if cint(line.get("from_card")) else "unlink"].append(log)
	return plan


def _e(value) -> str:
	return html.escape(str(value or ""))


def _text(value) -> str:
	"""Typed text for the printout: escaped, line breaks kept."""
	return _e(value).replace("\n", "<br>")


def _hours(value) -> str:
	return f"{flt(value):g}"


def render_card(card: dict, ctx: dict) -> str:
	"""The printable job card: one A4 page of plain HTML. Every value is
	escaped - client names, problems and comments are typed by people. The
	signature is embedded only if it is a PNG data URL."""
	lines = card.get("lines") or []
	items = card.get("items") or []
	signature = card.get("customer_signature")
	logo = ctx.get("logo_url")
	logo_html = f'<img src="{html.escape(logo, quote=True)}" alt="">' if logo else ""
	signed = card.get("status") == "Signed"

	def row(label, value):
		return f"<tr><th>{_e(label)}</th><td>{_e(value) or '&nbsp;'}</td></tr>" if value else ""

	line_rows = "".join(
		f"<tr><td class='nowrap'>{_e(l.get('date_label'))}</td><td>{_text(l.get('description'))}</td>"
		f"<td class='nowrap'>{_e(l.get('technician_name'))}</td><td class='num'>{_hours(l.get('hours'))}</td></tr>"
		for l in lines
	)
	item_rows = "".join(
		f"<tr><td>{_e(i.get('description'))}</td><td class='num'>{_hours(i.get('quantity'))}</td></tr>"
		for i in items
	)
	when = " - ".join(x for x in (card.get("time_in_label"), card.get("time_out_label")) if x)
	client_sign = (
		f"<img class='signature' src='{signature}' alt=''>"
		if signature and valid_signature(signature)
		else "<div class='sign-line'></div>"
	)
	satisfied = ""
	if signed:
		satisfied = _e(_("Work accepted as satisfactory") if cint(card.get("satisfied")) else _("Signed"))

	parts = [
		"<!doctype html><html><head><meta charset='utf-8'>",
		"<meta name='viewport' content='width=device-width, initial-scale=1'>",
		f"<title>{_e(_('Job card'))} {_e(card.get('name'))}</title>",
		f"<style>{PRINT_CSS}</style></head><body>",
		"<div class='toolbar no-print'>",
		f"<button onclick='window.print()'>{_e(_('Print or save as PDF'))}</button>",
		"</div>",
		"<main class='sheet'>",
		"<header>",
		f"<div class='brand'>{logo_html}<div class='brand-name'>{_e(ctx.get('brand_name'))}</div></div>",
		"<div class='title'>",
		f"<h1>{_e(_('Job card'))}</h1>",
		f"<div class='number'>{_e(card.get('name'))}</div>",
		f"<div class='status status-{_e((card.get('status') or '').lower())}'>{_e(_(card.get('status') or ''))}</div>",
		"</div></header>",
		"<section class='grid'>",
		f"<div><h2>{_e(_('Client'))}</h2><table class='kv'>",
		row(_("Client"), card.get("customer")),
		row(_("Contact"), card.get("contact_name")),
		row(_("Phone"), card.get("contact_phone")),
		row(_("Email"), card.get("contact_email")),
		"</table></div>",
		f"<div><h2>{_e(_('Job'))}</h2><table class='kv'>",
		row(_("Date"), card.get("date_label")),
		row(_("Service"), _(card.get("service_type") or "")),
		row(_("Location"), card.get("location")),
		row(_("Time"), when),
		row(_("Ticket"), f"#{card.get('ticket')} {card.get('ticket_subject') or ''}".strip() if card.get("ticket") else ""),
		row(_("Project"), card.get("project_name")),
		row(_("Technician"), card.get("technician_name")),
		"</table></div>",
		"</section>",
	]
	for heading, field in (
		(_("Work requested"), "work_requested"),
		(_("Work done"), "work_done"),
	):
		parts.append(
			f"<section><h2>{_e(heading)}</h2><div class='box'>{_text(card.get(field)) or '&nbsp;'}</div></section>"
		)
	parts.append(
		f"<section class='outcome'><h2>{_e(_('Outcome'))}</h2>"
		f"<div class='box'><b>{_e(_(card.get('work_status') or ''))}</b>"
		+ (f"<div class='recommend'>{_text(card.get('recommendations'))}</div>" if card.get("recommendations") else "")
		+ "</div></section>"
	)
	if lines:
		parts.append(
			f"<section><h2>{_e(_('Time spent'))}</h2><table class='list'><thead><tr>"
			f"<th>{_e(_('Date'))}</th><th>{_e(_('Work'))}</th><th>{_e(_('By'))}</th>"
			f"<th class='num'>{_e(_('Hours'))}</th></tr></thead><tbody>{line_rows}</tbody>"
			f"<tfoot><tr><td colspan='3'>{_e(_('Total'))}</td><td class='num'>{_hours(card.get('total_hours'))}</td></tr></tfoot>"
			"</table></section>"
		)
	if items:
		parts.append(
			f"<section><h2>{_e(_('Items used'))}</h2><table class='list'><thead><tr>"
			f"<th>{_e(_('Item'))}</th><th class='num'>{_e(_('Quantity'))}</th></tr></thead>"
			f"<tbody>{item_rows}</tbody></table></section>"
		)
	if ctx.get("contract_line"):
		parts.append(f"<p class='plan'>{_e(ctx['contract_line'])}</p>")
	parts += [
		"<section class='signoff'>",
		f"<div class='sign'><h2>{_e(_('Technician'))}</h2>",
		f"<div class='sign-name'>{_e(card.get('technician_name'))}</div>",
		"<div class='sign-line'></div>",
		f"<div class='sign-label'>{_e(_('Signature and date'))}</div></div>",
		f"<div class='sign'><h2>{_e(_('Client sign-off'))}</h2>",
		f"<div class='sign-name'>{_e(card.get('signed_by'))}"
		+ (f", {_e(card.get('signed_designation'))}" if card.get("signed_designation") else "")
		+ "</div>",
		client_sign,
		f"<div class='sign-label'>{_e(card.get('signed_on_label')) or _e(_('Name, signature, date and stamp'))}</div>",
		(f"<div class='accepted'>{satisfied}</div>" if satisfied else ""),
		(f"<div class='comments'>{_text(card.get('customer_comments'))}</div>" if card.get("customer_comments") else ""),
		"</div></section>",
		"<footer>",
		(f"<div class='company'>{_text(ctx.get('footer'))}</div>" if ctx.get("footer") else ""),
		f"<div class='generated'>{_e(_('Printed'))} {_e(ctx.get('generated_at'))}</div>",
		"</footer></main>",
		(
			"<script>window.addEventListener('load',function(){setTimeout(function(){window.print()},300)})</script>"
			if ctx.get("autoprint")
			else ""
		),
		"</body></html>",
	]
	return "".join(parts)


PRINT_CSS = """
@page { size: A4; margin: 12mm; }
* { box-sizing: border-box; }
body { margin: 0; background: #eef0f3; color: #1f2933; font: 12px/1.45 -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
.toolbar { position: sticky; top: 0; display: flex; justify-content: center; padding: 10px; background: #1f2933; }
.toolbar button { font: inherit; font-size: 13px; padding: 7px 16px; border: 0; border-radius: 6px; background: #fff; color: #1f2933; cursor: pointer; }
.sheet { width: 210mm; min-height: 297mm; margin: 16px auto; padding: 14mm; background: #fff; box-shadow: 0 1px 6px rgba(0,0,0,.15); }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 10px; border-bottom: 2px solid #1f2933; }
.brand { display: flex; align-items: center; gap: 10px; }
.brand img { max-height: 46px; max-width: 160px; object-fit: contain; }
.brand-name { font-size: 16px; font-weight: 700; }
.title { text-align: right; }
h1 { margin: 0; font-size: 20px; letter-spacing: .5px; text-transform: uppercase; }
.number { font-size: 14px; font-weight: 600; margin-top: 2px; }
.status { display: inline-block; margin-top: 4px; padding: 1px 8px; border-radius: 10px; font-size: 11px; background: #e5e7eb; }
.status-signed { background: #d1fae5; color: #065f46; }
.status-cancelled { background: #fee2e2; color: #991b1b; }
h2 { margin: 14px 0 5px; font-size: 11px; text-transform: uppercase; letter-spacing: .6px; color: #52606d; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
table { width: 100%; border-collapse: collapse; }
.kv th { width: 34%; text-align: left; font-weight: 500; color: #52606d; padding: 2px 6px 2px 0; vertical-align: top; }
.kv td { padding: 2px 0; vertical-align: top; }
.box { border: 1px solid #cbd2d9; border-radius: 4px; padding: 7px 9px; min-height: 34px; }
.recommend { margin-top: 5px; }
.list th, .list td { border: 1px solid #cbd2d9; padding: 4px 6px; text-align: left; vertical-align: top; }
.list thead th { background: #f5f7fa; font-weight: 600; }
.list tfoot td { font-weight: 700; background: #f5f7fa; }
.num { text-align: right !important; white-space: nowrap; }
.nowrap { white-space: nowrap; }
.plan { margin: 10px 0 0; color: #52606d; }
.signoff { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 18px; page-break-inside: avoid; }
.sign-name { min-height: 16px; font-weight: 600; }
.sign-line { height: 46px; border-bottom: 1px solid #1f2933; }
.signature { display: block; max-height: 70px; max-width: 100%; border-bottom: 1px solid #1f2933; }
.sign-label { font-size: 10px; color: #52606d; margin-top: 3px; }
.accepted { margin-top: 5px; font-weight: 600; color: #065f46; }
.comments { margin-top: 4px; font-style: italic; }
footer { margin-top: 22px; padding-top: 8px; border-top: 1px solid #cbd2d9; display: flex; justify-content: space-between; gap: 16px; font-size: 10px; color: #52606d; }
@media print {
  body { background: #fff; }
  .no-print { display: none !important; }
  .sheet { width: auto; min-height: 0; margin: 0; padding: 0; box-shadow: none; }
}
@media (max-width: 820px) {
  .sheet { width: auto; min-height: 0; margin: 0; padding: 16px; }
  .grid, .signoff { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can do this"), frappe.PermissionError)


def _is_clients_card(doc) -> bool:
	return bool(doc.customer) and doc.customer in get_customer(frappe.session.user)


def _assert_can_view(doc) -> None:
	if is_agent():
		return
	if doc.status != "Cancelled" and _is_clients_card(doc):
		return
	frappe.throw(_("Not permitted"), frappe.PermissionError)


def _who(user) -> str:
	return get_fullname(user) if user else ""


def _contact_details(contact: str | None, email: str | None) -> dict:
	out = {"contact": None, "contact_name": "", "contact_phone": "", "contact_email": email or ""}
	if contact and frappe.db.exists("Contact", contact):
		c = frappe.db.get_value(
			"Contact", contact, ["name", "full_name", "first_name", "phone", "mobile_no", "email_id"], as_dict=True
		)
		out.update(
			contact=c.name,
			contact_name=c.full_name or c.first_name or "",
			contact_phone=c.mobile_no or c.phone or "",
			contact_email=c.email_id or email or "",
		)
	return out


def _line_text(log, subtask_subjects) -> str:
	if log.description:
		return log.description
	if log.subtask and subtask_subjects.get(log.subtask):
		return subtask_subjects[log.subtask]
	return _("Work on the ticket")


def _ticket_lines(ticket: str) -> list:
	"""The ticket's logged time that is not on a job card yet."""
	logs = frappe.get_all(
		"HD Time Log",
		filters={"ticket": ticket, "job_card": ["is", "not set"]},
		fields=["name", "date", "hours", "description", "subtask", "logged_by"],
		order_by="date asc, creation asc",
	)
	subjects = contracts._subjects("HD Ticket Subtask", {l.subtask for l in logs if l.subtask})
	return [
		{
			"date": l.date,
			"hours": flt(l.hours),
			"description": _line_text(l, subjects),
			"technician": l.logged_by,
			"technician_name": _who(l.logged_by),
			"time_log": l.name,
			"from_card": 0,
		}
		for l in logs
	]


def _payload(doc) -> dict:
	out = {f: doc.get(f) for f in CARD_FIELDS}
	out["lines"] = [{"name": l.name, **{f: l.get(f) for f in LINE_FIELDS}} for l in doc.lines]
	out["items"] = [{"name": i.name, "description": i.description, "quantity": i.quantity} for i in doc.items]
	out["ticket_subject"] = (
		frappe.db.get_value("HD Ticket", doc.ticket, "subject") if doc.ticket else None
	)
	agent = is_agent()
	locked = doc.status in ("Signed", "Cancelled")
	out["can_edit"] = agent and not locked
	out["can_sign"] = not locked and (agent or doc.status == "Completed")
	out["can_cancel"] = agent and doc.status != "Cancelled" and (doc.status != "Signed" or is_agent_manager())
	if not agent:
		# The client sees the card as printed: names, not agents' addresses,
		# and nothing of the time ledger behind it.
		out.pop("technician", None)
		for line in out["lines"]:
			for key in ("time_log", "from_card", "technician"):
				line.pop(key, None)
	return out


def _apply_lines(doc, incoming: list, log_time: bool) -> None:
	"""Save the card's lines and keep the time ledger in step (plan_lines)."""
	if len(incoming) > MAX_LINES:
		frappe.throw(_("A job card can have at most {0} time lines").format(MAX_LINES))
	today = getdate(nowdate())
	clean = []
	for line in incoming:
		hours = flt(line.get("hours"))
		if hours <= 0:
			continue
		if hours > contracts.MAX_HOURS_PER_ENTRY:
			frappe.throw(_("A time line can be at most {0} hours").format(contracts.MAX_HOURS_PER_ENTRY))
		on = getdate(line.get("date") or doc.date)
		if on > today:
			frappe.throw(_("Time can't be logged on a future date"))
		technician = line.get("technician") or doc.technician or frappe.session.user
		clean.append(
			{
				"date": on,
				"hours": round(hours, 2),
				"description": (line.get("description") or "").strip()[:1000] or None,
				"technician": technician,
				"technician_name": _who(technician),
				"time_log": line.get("time_log") or None,
				"from_card": cint(line.get("from_card")),
			}
		)
	old = [{"time_log": l.time_log, "from_card": l.from_card} for l in doc.lines]
	plan = plan_lines(old, clean, log_time)

	for log in plan["delete"]:
		if frappe.db.exists("HD Time Log", log):
			frappe.delete_doc("HD Time Log", log, ignore_permissions=True)
	for log in plan["unlink"]:
		if frappe.db.get_value("HD Time Log", log, "job_card") == doc.name:
			frappe.db.set_value("HD Time Log", log, "job_card", None)
	for log in plan["link"]:
		current = frappe.db.get_value("HD Time Log", log, ["job_card", "customer", "ticket"], as_dict=True)
		if not current:
			continue  # removed from the ledger since: the card keeps its copy
		if current.job_card and current.job_card != doc.name:
			frappe.throw(_("Some of this time is already on job card {0}").format(current.job_card))
		if current.customer != doc.customer and not (doc.ticket and current.ticket == doc.ticket):
			frappe.throw(_("A time line belongs to another client"))
		frappe.db.set_value("HD Time Log", log, "job_card", doc.name)
	by_log = {l["time_log"]: l for l in clean if l["time_log"]}
	for log in plan["update"]:
		line = by_log[log]
		if frappe.db.exists("HD Time Log", log):

			def change(log=log, line=line):
				frappe.db.set_value(
					"HD Time Log",
					log,
					{"date": line["date"], "hours": line["hours"], "description": line["description"]},
				)

			contracts._record(doc.customer, line["date"], change)
	for i in plan["create"]:
		line = clean[i]
		created = []

		def change(line=line, created=created):
			created.append(
				contracts._new_log(
					doc.customer, doc.ticket, None, line["date"], line["hours"],
					line["description"] or _("Job card {0}").format(doc.name),
					job_card=doc.name, logged_by=line["technician"],
				)
			)

		contracts._record(doc.customer, line["date"], change)
		line["time_log"], line["from_card"] = created[0], 1

	doc.set("lines", [])
	for line in clean:
		doc.append("lines", line)


def validate_card(doc) -> None:
	"""HD Job Card.validate - the same rules for the desk form."""
	if doc.status not in STATUSES:
		doc.status = "Open"
	if doc.service_type not in SERVICE_TYPES:
		doc.service_type = "Remote"
	if doc.work_status not in WORK_STATUSES:
		doc.work_status = "Resolved"
	if not doc.customer:
		frappe.throw(_("Pick the client this job card is for"))
	if doc.technician:
		doc.technician_name = _who(doc.technician)
	if doc.time_in and doc.time_out and to_timedelta(doc.time_out) < to_timedelta(doc.time_in):
		frappe.throw(_("Time out is before time in"))
	doc.total_hours = total_hours(doc.lines)


def _log_on_ticket(ticket, action: str) -> None:
	if not ticket:
		return
	try:
		from helpdesk.helpdesk.doctype.hd_ticket_activity.hd_ticket_activity import log_ticket_activity

		log_ticket_activity(ticket, action)
	except Exception:
		pass


# ---------------------------------------------------------------------------
# API - agents
# ---------------------------------------------------------------------------


@frappe.whitelist()
def new_job_card(ticket: str | None = None, customer: str | None = None) -> dict:
	"""A filled-in card to start from; nothing is saved yet."""
	_assert_agent()
	me = frappe.session.user
	card = {
		"name": None,
		"status": "Open",
		"date": nowdate(),
		"customer": customer,
		"ticket": None,
		"ticket_subject": None,
		"project": None,
		"service_type": "Remote",
		"location": "",
		"time_in": None,
		"time_out": None,
		"technician": me,
		"technician_name": _who(me),
		"work_requested": "",
		"work_done": "",
		"work_status": "Resolved",
		"recommendations": "",
		"lines": [],
		"items": [],
		"can_edit": True,
		"can_sign": False,
		"can_cancel": False,
		**_contact_details(None, None),
	}
	if ticket:
		contracts._assert_ticket(ticket)
		t = frappe.get_doc("HD Ticket", ticket)
		problem = strip_html(t.description or "").strip()
		card.update(
			ticket=t.name,
			ticket_subject=t.subject,
			customer=t.customer or customer,
			project=t.get("project"),
			work_requested=(t.subject or "") + (f"\n\n{problem[:1500]}" if problem else ""),
			lines=_ticket_lines(t.name),
			**_contact_details(t.contact, t.raised_by),
		)
	return card


@frappe.whitelist()
def get_job_card(name: str) -> dict:
	doc = frappe.get_doc("HD Job Card", name)
	_assert_can_view(doc)
	return _payload(doc)


@frappe.whitelist()
def save_job_card(data) -> str:
	_assert_agent()
	data = frappe._dict(frappe.parse_json(data) if isinstance(data, str) else (data or {}))
	if data.get("name"):
		doc = frappe.get_doc("HD Job Card", data.name)
		if doc.status in ("Signed", "Cancelled"):
			frappe.throw(_("A signed or cancelled job card can't be changed"))
	else:
		doc = frappe.new_doc("HD Job Card")
	for field in EDITABLE:
		if field in data:
			value = data.get(field)
			doc.set(field, (value.strip() if isinstance(value, str) else value) or None)
	if doc.ticket:
		contracts._assert_ticket(doc.ticket)
		if not doc.customer:
			doc.customer = frappe.db.get_value("HD Ticket", doc.ticket, "customer")
	if "items" in data:
		doc.set("items", [])
		for item in data.get("items") or []:
			description = (item.get("description") or "").strip()
			if description:
				doc.append(
					"items", {"description": description[:140], "quantity": flt(item.get("quantity")) or 1}
				)
	if doc.is_new():
		doc.insert(ignore_permissions=True)
		_log_on_ticket(doc.ticket, f"opened job card {doc.name}")
	if "lines" in data:
		_apply_lines(doc, data.get("lines") or [], bool(cint(data.get("log_time", 1))))
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def set_status(name: str, status: str) -> dict:
	"""Open <-> Completed, or Cancelled (a signed card: managers only)."""
	_assert_agent()
	doc = frappe.get_doc("HD Job Card", name)
	if status not in ("Open", "Completed", "Cancelled"):
		frappe.throw(_("Invalid status"))
	if doc.status == "Cancelled":
		frappe.throw(_("This job card is cancelled"))
	if doc.status == "Signed" and (status != "Cancelled" or not is_agent_manager()):
		frappe.throw(_("A signed job card can only be cancelled, by a manager"), frappe.PermissionError)
	doc.status = status
	doc.save(ignore_permissions=True)
	if status == "Cancelled":
		_log_on_ticket(doc.ticket, f"cancelled job card {doc.name}")
	return _payload(doc)


@frappe.whitelist()
def delete_job_card(name: str) -> bool:
	"""An unsigned card goes, with the time it created; time it took from the
	ticket stays logged and comes off the card."""
	_assert_agent()
	doc = frappe.get_doc("HD Job Card", name)
	if doc.status == "Signed":
		frappe.throw(_("A signed job card can't be deleted. A manager can cancel it."))
	for line in doc.lines:
		if not line.time_log or not frappe.db.exists("HD Time Log", line.time_log):
			continue
		if cint(line.from_card):
			frappe.delete_doc("HD Time Log", line.time_log, ignore_permissions=True)
	frappe.db.set_value("HD Time Log", {"job_card": doc.name}, "job_card", None)
	frappe.delete_doc("HD Job Card", doc.name, ignore_permissions=True)
	_log_on_ticket(doc.ticket, f"deleted job card {doc.name}")
	return True


@frappe.whitelist()
def list_job_cards(
	ticket: str | None = None,
	customer: str | None = None,
	status: str | None = None,
	search: str | None = None,
	limit: int = 100,
) -> list:
	_assert_agent()
	filters = {}
	if ticket:
		filters["ticket"] = ticket
	if customer:
		filters["customer"] = customer
	if status in STATUSES:
		filters["status"] = status
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [
			["name", "like", like],
			["customer", "like", like],
			["ticket", "like", like],
			["contact_name", "like", like],
		]
	return frappe.get_all(
		"HD Job Card",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "status", "date", "customer", "ticket", "service_type", "technician_name",
			"total_hours", "work_status", "signed_by", "signed_on",
		],
		order_by="date desc, creation desc",
		limit_page_length=max(1, min(cint(limit) or 100, 500)),
	)


@frappe.whitelist()
def get_print_settings() -> dict:
	frappe.only_for(["Agent Manager", "System Manager"])
	s = frappe.get_single("HD Job Card Settings")
	return {"footer": s.footer or "", "show_contract_usage": cint(s.show_contract_usage)}


@frappe.whitelist()
def save_print_settings(footer: str | None = None, show_contract_usage: int = 1) -> bool:
	frappe.only_for(["Agent Manager", "System Manager"])
	s = frappe.get_single("HD Job Card Settings")
	s.footer = (footer or "").strip()[:2000] or None
	s.show_contract_usage = 1 if cint(show_contract_usage) else 0
	s.save(ignore_permissions=True)
	return True


# ---------------------------------------------------------------------------
# API - sign-off (agents, and the card's client)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def sign_job_card(
	name: str,
	signed_by: str,
	designation: str | None = None,
	signature: str | None = None,
	comments: str | None = None,
	satisfied: int = 1,
) -> dict:
	"""The client signs the card off: on the agent's device, in the portal
	(cards marked Completed), or - recorded by the agent - on paper."""
	doc = frappe.get_doc("HD Job Card", name)
	agent = is_agent()
	if not agent:
		if not _is_clients_card(doc):
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		if doc.status != "Completed":
			frappe.throw(_("This job card isn't ready for your signature yet"))
	if doc.status in ("Signed", "Cancelled"):
		frappe.throw(_("This job card is already {0}").format(_(doc.status).lower()))
	signed_by = (signed_by or "").strip()[:140]
	if not signed_by:
		frappe.throw(_("Enter the name of the person signing"))
	if signature and not valid_signature(signature):
		frappe.throw(_("The signature could not be read. Clear it and sign again."))
	if not signature and not agent:
		frappe.throw(_("Sign in the box first"))
	doc.status = "Signed"
	doc.signed_by = signed_by
	doc.signed_designation = (designation or "").strip()[:140] or None
	doc.customer_signature = signature or None
	doc.customer_comments = (comments or "").strip()[:2000] or None
	doc.satisfied = 1 if cint(satisfied) else 0
	doc.signed_on = now_datetime()
	doc.save(ignore_permissions=True)
	_log_on_ticket(doc.ticket, f"job card {doc.name} signed off by {signed_by}")
	return _payload(doc)


# ---------------------------------------------------------------------------
# API - the client's portal
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_my_job_cards() -> list:
	if is_agent():
		return []
	companies = get_customer(frappe.session.user)
	if not companies:
		return []
	return frappe.get_all(
		"HD Job Card",
		filters={"customer": ["in", companies], "status": ["!=", "Cancelled"]},
		fields=[
			"name", "status", "date", "customer", "ticket", "service_type", "technician_name",
			"total_hours", "work_status", "signed_by", "signed_on",
		],
		order_by="date desc, creation desc",
		limit_page_length=50,
	)


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------


def clock(value) -> str:
	"""A Time field's value (timedelta, or "H:MM:SS" text) as "HH:MM"."""
	if value in (None, ""):
		return ""
	if hasattr(value, "total_seconds"):
		minutes = int(value.total_seconds()) // 60
	else:
		hours, _sep, rest = str(value).partition(":")
		minutes = int(hours or 0) * 60 + int((rest or "0").split(":")[0] or 0)
	return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _contract_line(doc) -> str | None:
	try:
		c = contracts.active_contract(doc.customer, doc.date)
		if not c:
			return None
		u = contracts.contract_usage(c, doc.date)
	except Exception:
		return None
	return _("Support plan {0}: {1} of {2} hours used in {3}.").format(
		c.contract_name, f"{u['used']:g}", f"{u['included']:g}", u["period_label"]
	)


@frappe.whitelist()
def print_job_card(name: str, autoprint: int = 0):
	"""The job card as a printable page (print, or save as PDF, from the
	browser). Agents, and the card's own client."""
	doc = frappe.get_doc("HD Job Card", name)
	_assert_can_view(doc)
	card = _payload(doc)
	card["date_label"] = format_date(doc.date) if doc.date else ""
	card["time_in_label"] = clock(doc.time_in)
	card["time_out_label"] = clock(doc.time_out)
	card["signed_on_label"] = format_datetime(doc.signed_on) if doc.signed_on else ""
	card["project_name"] = (
		frappe.db.get_value("HD Project", doc.project, "project_name") if doc.project else None
	)
	for line in card["lines"]:
		line["date_label"] = format_date(line["date"]) if line.get("date") else ""
	settings = frappe.get_single("HD Job Card Settings")
	brand_name, logo = frappe.db.get_value("HD Settings", "HD Settings", ["brand_name", "brand_logo"]) or (None, None)
	ctx = {
		"brand_name": brand_name or frappe.db.get_single_value("Website Settings", "app_name") or "",
		"logo_url": (get_url(logo) if logo and logo.startswith("/") else logo) or None,
		"footer": settings.footer,
		"contract_line": _contract_line(doc) if cint(settings.show_contract_usage) else None,
		"generated_at": format_datetime(now_datetime()),
		"autoprint": cint(autoprint),
	}
	return Response(render_card(card, ctx), mimetype="text/html")
