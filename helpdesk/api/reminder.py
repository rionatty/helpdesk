# Reminders API.
#
# Any authenticated user (agent or customer portal) can manage their own
# reminders. The scheduler publishes realtime events for due reminders and
# optionally sends email.

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now, now_datetime


@frappe.whitelist()
def create_reminder(
	message: str,
	remind_at: str,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	send_email: bool | int = False,
	recipients: str | None = None,
	add_to_calendar: bool | int = False,
) -> str:
	"""Create a personal reminder. Any authenticated user. If `recipients` are
	given, they also get notified — with an optional calendar invite."""
	if not (message or "").strip():
		frappe.throw(_("Message is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Reminder",
			"message": message.strip(),
			"remind_at": remind_at,
			"reference_doctype": reference_doctype or None,
			"reference_name": reference_name or None,
			"status": "Pending",
			"send_email": 1 if send_email else 0,
			"recipients": (recipients or "").strip() or None,
			"add_to_calendar": 1 if add_to_calendar else 0,
		}
	).insert(ignore_permissions=True)
	# Send the invite to any extra recipients up front (books their calendar).
	if doc.recipients:
		_send_reminder_invite(doc)
	return doc.name


def _outgoing_sender() -> str | None:
	"""Best available outgoing sender — frappe.sendmail needs one, and it isn't
	always flagged Default Outgoing."""
	return frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")


def _parse_recipients(raw: str | None) -> list[str]:
	"""Split a comma/semicolon/newline-separated recipient string into valid
	email addresses."""
	if not raw:
		return []
	import re

	parts = [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]
	out = []
	for p in parts:
		try:
			frappe.utils.validate_email_address(p, throw=True)
			out.append(p)
		except Exception:
			continue
	return out


def _ics_escape(text: str) -> str:
	return (
		(text or "")
		.replace("\\", "\\\\")
		.replace(";", "\\;")
		.replace(",", "\\,")
		.replace("\n", "\\n")
	)


def _build_ics(doc, organizer: str | None = None, attendees: list | None = None) -> str:
	"""A single-event .ics meeting REQUEST at the reminder time (UTC).

	Using METHOD:REQUEST with ORGANIZER + ATTENDEE (RSVP) makes Outlook/Gmail
	treat it as an actionable invite that lands on the calendar, rather than a
	plain file attachment.
	"""
	import pytz

	start = frappe.utils.get_datetime(doc.remind_at)  # naive, system tz
	tz = pytz.timezone(frappe.utils.get_system_timezone())
	start_utc = tz.localize(start).astimezone(pytz.utc)
	end_utc = start_utc + timedelta(minutes=30)
	stamp = datetime.now(pytz.utc)
	fmt = lambda d: d.strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
	summary = _ics_escape((doc.message or "Reminder").replace("\n", " ")[:200])

	lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		"PRODID:-//CyveTech//Helpdesk//EN",
		"CALSCALE:GREGORIAN",
		"METHOD:REQUEST",
		"BEGIN:VEVENT",
		f"UID:{doc.name}@cyvetech-helpdesk",
		f"DTSTAMP:{fmt(stamp)}",
		f"DTSTART:{fmt(start_utc)}",
		f"DTEND:{fmt(end_utc)}",
		f"SUMMARY:{summary}",
		f"DESCRIPTION:{_ics_escape(doc.message or '')}",
		"SEQUENCE:0",
		"STATUS:CONFIRMED",
		"TRANSP:OPAQUE",
	]
	if organizer:
		lines.append(f"ORGANIZER;CN={organizer}:mailto:{organizer}")
	for a in attendees or []:
		lines.append(
			"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;"
			f"PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN={a}:mailto:{a}"
		)
	lines += [
		"BEGIN:VALARM",
		"TRIGGER:-PT10M",
		"ACTION:DISPLAY",
		"DESCRIPTION:Reminder",
		"END:VALARM",
		"END:VEVENT",
		"END:VCALENDAR",
	]
	return "\r\n".join(lines)


def _reminder_ref_line(doc) -> str:
	if not doc.reference_name:
		return ""
	return (
		f"<p><strong>Reference:</strong> "
		f"{frappe.utils.escape_html(doc.reference_doctype or '')} — "
		f"{frappe.utils.escape_html(doc.reference_name)}</p>"
	)


def _send_reminder_invite(doc) -> None:
	"""Email the extra recipients about the reminder, attaching a calendar
	invite when requested. Best-effort."""
	to = _parse_recipients(doc.recipients)
	if not to:
		return
	sender = _outgoing_sender()
	if not sender:
		frappe.log_error(
			title="Reminder invite skipped",
			message="No outgoing Email Account configured.",
		)
		return
	setter = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner
	when = frappe.utils.format_datetime(doc.remind_at, "medium")
	attachments = (
		[
			{
				"fname": "invite.ics",
				"fcontent": _build_ics(doc, organizer=sender, attendees=to),
				# The method param is what makes Outlook treat it as an invite.
				"content_type": "text/calendar; charset=UTF-8; method=REQUEST",
			}
		]
		if doc.add_to_calendar
		else []
	)
	tail = (
		f"<p style='color:#888;font-size:12px'>{_('Add the attached invite to your calendar.')}</p>"
		if doc.add_to_calendar
		else ""
	)
	try:
		frappe.sendmail(
			recipients=to,
			sender=sender,
			subject=_("Reminder: {0}").format(doc.message[:80]),
			message=f"""
				<p>{frappe.utils.escape_html(setter)} {_('scheduled a reminder for you')}:</p>
				<p><strong>{when}</strong></p>
				<blockquote style="border-left:3px solid #ccc;margin:8px 0;padding:4px 12px">
					{frappe.utils.escape_html(doc.message)}
				</blockquote>
				{_reminder_ref_line(doc)}
				{tail}
			""",
			attachments=attachments,
			reference_doctype="HD Reminder",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="Reminder invite email failed", message=frappe.get_traceback()
		)


@frappe.whitelist()
def get_my_reminders() -> list[dict]:
	"""Non-dismissed, non-performed reminders for the bell popover."""
	return frappe.get_all(
		"HD Reminder",
		filters={
			"owner": frappe.session.user,
			"status": ["in", ["Pending", "Notified"]],
		},
		fields=[
			"name",
			"message",
			"remind_at",
			"reference_doctype",
			"reference_name",
			"status",
			"send_email",
			"recipients",
			"add_to_calendar",
		],
		order_by="remind_at asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def get_all_my_reminders() -> list[dict]:
	"""All reminders for the current user (all statuses), newest first."""
	return frappe.get_all(
		"HD Reminder",
		filters={"owner": frappe.session.user},
		fields=[
			"name",
			"message",
			"remind_at",
			"reference_doctype",
			"reference_name",
			"status",
			"send_email",
			"recipients",
			"add_to_calendar",
		],
		order_by="remind_at desc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def mark_performed(name: str) -> bool:
	"""Mark a reminder as performed. Only the owner may do this."""
	owner = frappe.db.get_value("HD Reminder", name, "owner")
	if owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.db.set_value("HD Reminder", name, "status", "Performed", update_modified=False)
	return True


@frappe.whitelist()
def update_reminder(
	name: str,
	message: str,
	remind_at: str,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
	send_email: bool | int | None = None,
	recipients: str | None = None,
	add_to_calendar: bool | int | None = None,
) -> bool:
	"""Edit a reminder and reset it to Pending. Only the owner may do this.
	Any field left as None is not touched."""
	doc = frappe.get_doc("HD Reminder", name)
	if doc.owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not (message or "").strip():
		frappe.throw(_("Message is required"))
	doc.message = message.strip()
	doc.remind_at = remind_at
	doc.status = "Pending"
	if reference_doctype is not None:
		doc.reference_doctype = reference_doctype or None
	if reference_name is not None:
		doc.reference_name = reference_name or None
	if send_email is not None:
		doc.send_email = 1 if int(send_email) else 0
	if recipients is not None:
		doc.recipients = (recipients or "").strip() or None
	if add_to_calendar is not None:
		doc.add_to_calendar = 1 if int(add_to_calendar) else 0
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def dismiss_reminder(name: str) -> bool:
	"""Dismiss a reminder. Only the owner may dismiss."""
	owner = frappe.db.get_value("HD Reminder", name, "owner")
	if owner != frappe.session.user:
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	frappe.db.set_value("HD Reminder", name, "status", "Dismissed", update_modified=False)
	return True


def send_due_reminders() -> None:
	"""Scheduled every 5 minutes. Publishes realtime events for overdue Pending
	reminders, sends email when requested, then marks them Notified."""
	overdue = frappe.get_all(
		"HD Reminder",
		filters={"status": "Pending", "remind_at": ["<=", now()]},
		fields=[
			"name",
			"owner",
			"message",
			"reference_doctype",
			"reference_name",
			"send_email",
			"recipients",
		],
		ignore_permissions=True,
	)
	for r in overdue:
		# Realtime popup in the browser (owner only)
		frappe.publish_realtime(
			"helpdesk:reminder_due",
			{
				"name": r.name,
				"message": r.message,
				"reference_doctype": r.reference_doctype,
				"reference_name": r.reference_name,
			},
			user=r.owner,
		)
		# Email the owner (if opted in) and any extra recipients.
		to = []
		if r.send_email:
			to.append(frappe.db.get_value("User", r.owner, "email") or r.owner)
		to += _parse_recipients(r.recipients)
		to = list(dict.fromkeys([e for e in to if e]))
		if to:
			sender = _outgoing_sender()
			if not sender:
				frappe.log_error(
					title="Reminder email skipped",
					message="No outgoing Email Account configured.",
				)
			else:
				try:
					frappe.sendmail(
						recipients=to,
						sender=sender,
						subject=_("Reminder: {0}").format(r.message[:80]),
						message=f"""
							<p>{_('This is a reminder')}:</p>
							<blockquote style="border-left:3px solid #ccc;margin:8px 0;padding:4px 12px">
								{frappe.utils.escape_html(r.message)}
							</blockquote>
							{_reminder_ref_line(r)}
						""",
						reference_doctype="HD Reminder",
						reference_name=r.name,
						now=True,
					)
				except Exception:
					frappe.log_error(
						frappe.get_traceback(), "HD Reminder email failed"
					)

		frappe.db.set_value(
			"HD Reminder", r.name, "status", "Notified", update_modified=False
		)
	if overdue:
		frappe.db.commit()


# ---------------------------------------------------------------------------
# SLA-based ticket reminders (auto-created ahead of SLA deadlines)
# ---------------------------------------------------------------------------

SLA_RESPONSE_TAG = "[SLA] First response"
SLA_RESOLUTION_TAG = "[SLA] Resolution"


def _ticket_reminder_targets(ticket_row) -> list:
	"""The ticket's assigned agents; unassigned tickets fall back to enabled
	Agent Managers (someone has to triage before the SLA blows)."""
	agents = []
	try:
		parsed = frappe.parse_json(ticket_row._assign or "[]")
		if isinstance(parsed, list):
			agents = [a for a in parsed if a]
	except Exception:
		agents = []
	if agents:
		return agents
	managers = frappe.get_all(
		"Has Role",
		filters={"role": "Agent Manager", "parenttype": "User"},
		pluck="parent",
	)
	if not managers:
		return []
	return frappe.get_all(
		"User",
		filters=[
			["name", "in", managers],
			["enabled", "=", 1],
			["name", "not in", ["Administrator", "Guest"]],
		],
		pluck="name",
	)


def _ensure_sla_reminder(ticket, agent, tag, deadline, remind_at) -> None:
	"""Create (or retime) one agent's SLA reminder for a ticket. The (owner,
	ticket, tag) triple is the dedupe key so each deadline reminds once."""
	existing = frappe.get_all(
		"HD Reminder",
		filters={
			"reference_doctype": "HD Ticket",
			"reference_name": ticket.name,
			"owner": agent,
			"message": ["like", f"{tag}%"],
		},
		fields=["name", "status", "remind_at"],
		limit_page_length=1,
		ignore_permissions=True,
	)
	if existing:
		row = existing[0]
		# Deadline moved (SLA reset/pause) — retime a still-pending reminder.
		if row.status == "Pending" and str(row.remind_at) != str(remind_at):
			frappe.db.set_value(
				"HD Reminder", row.name, "remind_at", remind_at,
				update_modified=False,
			)
		return
	msg = (
		f"{tag} for #{ticket.name} due "
		f"{frappe.utils.format_datetime(deadline, 'medium')} — "
		f"{ticket.subject or ''}"
	)[:500]
	doc = frappe.get_doc(
		{
			"doctype": "HD Reminder",
			"message": msg,
			"remind_at": remind_at,
			"reference_doctype": "HD Ticket",
			"reference_name": ticket.name,
			"status": "Pending",
			"send_email": 1,
		}
	).insert(ignore_permissions=True)
	# Owner drives who gets the popup/email; the scheduler runs as Administrator.
	frappe.db.set_value(
		"HD Reminder", doc.name, "owner", agent, update_modified=False
	)


def create_sla_reminders() -> None:
	"""Scheduler: auto-create agent reminders ahead of ticket SLA deadlines
	(first response and resolution), using the lead times configured in HD
	Settings. Runs on the same 5-minute cron as send_due_reminders, before it,
	so a reminder created inside its lead window fires on the same tick."""
	resp_lead = cint(
		frappe.db.get_single_value("HD Settings", "sla_response_reminder_lead")
	)
	reso_lead = cint(
		frappe.db.get_single_value("HD Settings", "sla_resolution_reminder_lead")
	)
	if not resp_lead and not reso_lead:
		return
	now_dt = now_datetime()

	if resp_lead:
		rows = frappe.get_all(
			"HD Ticket",
			filters={
				"response_by": [
					"between", [now_dt, add_to_date(now_dt, minutes=resp_lead)],
				],
				"first_responded_on": ["is", "not set"],
				"agreement_status": "First Response Due",
			},
			fields=["name", "subject", "response_by", "_assign"],
			ignore_permissions=True,
		)
		for t in rows:
			remind_at = max(add_to_date(t.response_by, minutes=-resp_lead), now_dt)
			for agent in _ticket_reminder_targets(t):
				_ensure_sla_reminder(
					t, agent, SLA_RESPONSE_TAG, t.response_by, remind_at
				)

	if reso_lead:
		rows = frappe.get_all(
			"HD Ticket",
			filters={
				"resolution_by": [
					"between", [now_dt, add_to_date(now_dt, minutes=reso_lead)],
				],
				"resolution_date": ["is", "not set"],
			},
			fields=["name", "subject", "resolution_by", "_assign"],
			ignore_permissions=True,
		)
		for t in rows:
			remind_at = max(add_to_date(t.resolution_by, minutes=-reso_lead), now_dt)
			for agent in _ticket_reminder_targets(t):
				_ensure_sla_reminder(
					t, agent, SLA_RESOLUTION_TAG, t.resolution_by, remind_at
				)
	frappe.db.commit()
