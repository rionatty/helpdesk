# Copyright (c) 2026, rionatty and contributors
# The WhatsApp channel, through Meta's WhatsApp Cloud API.
#
# Inbound: Meta calls webhook() for every message sent to the business number.
# The call is verified first: on GET, the verify token; on POST, the
# X-Hub-Signature-256 HMAC of the raw body under the app secret. It is then
# answered at once and processed by a background job. A message joins the
# sender's open ticket, or a ticket resolved within the last few days (which
# it reopens), or else starts a new ticket. Photos, documents, voice notes and
# videos are downloaded and attached.
#
# Outbound: an agent's reply on a WhatsApp ticket goes back on WhatsApp
# (reply_via_agent calls send_agent_reply). WhatsApp only allows free text
# within 24 hours of the customer's last message. After that it needs an
# approved template, if one is configured.
#
# Loop guard: the only automatic message is the new-ticket acknowledgement.
# It is capped per number (ACK_LIMITS), never sent to our own number, and only
# answers messages a person wrote. The customer may have no email address:
# such tickets keep raised_by empty, and every email path skips them.
#
# Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api

import hashlib
import hmac
import html
import json
import mimetypes
import re
import time
from datetime import datetime, timedelta
from html.parser import HTMLParser

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, now_datetime
from pypika.functions import Replace
from werkzeug.wrappers import Response

GRAPH = "https://graph.facebook.com"
DEFAULT_VERSION = "v23.0"
MAX_TEXT = 4096  # WhatsApp's limit for one text message
MAX_MEDIA_BYTES = 16 * 1024 * 1024
WINDOW_HOURS = 24  # free-form replies are allowed this long after the customer writes
ACK_LIMITS = ((3600, 2), (86400, 4))  # (seconds, acknowledgements per number)
DEFAULT_ACK = (
	"Thanks{name}! We have your message and opened ticket #{ticket}. "
	"We will reply here as soon as we can."
)
# Message types that carry no words from the customer: logged, never a ticket.
SILENT_TYPES = {"reaction", "system", "unsupported", "ephemeral", "request_welcome", "unknown"}
MEDIA_TYPES = ("image", "document", "audio", "video", "sticker")
STATUS_RANK = {"Sent": 1, "Delivered": 2, "Read": 3}


class WhatsAppError(Exception):
	def __init__(self, message, code=None):
		super().__init__(message)
		self.code = code


# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def digits(value) -> str:
	return re.sub(r"\D", "", str(value or ""))


def verify_signature(secret: str | None, body: bytes, header: str | None) -> bool:
	"""Meta signs each webhook POST: X-Hub-Signature-256 is
	"sha256=" + HMAC-SHA256(app secret, raw body). Without a secret nothing
	is trusted."""
	if not secret or not header or not header.startswith("sha256="):
		return False
	expected = hmac.new(secret.encode(), body or b"", hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, header[len("sha256=") :].strip().lower())


def parse_message(m: dict) -> tuple:
	"""(kind, text, media) from one webhook message. `media` is (id, mime,
	filename) for attachments, else None; `text` is what the customer wrote,
	or a short description of what they sent."""
	kind = m.get("type") or "unknown"
	if kind == "text":
		return kind, ((m.get("text") or {}).get("body") or "").strip(), None
	if kind in MEDIA_TYPES:
		part = m.get(kind) or {}
		caption = (part.get("caption") or "").strip()
		label = {
			"image": _("Photo"),
			"document": _("Document"),
			"audio": _("Voice message"),
			"video": _("Video"),
			"sticker": _("Sticker"),
		}[kind]
		filename = part.get("filename")
		if kind == "document" and filename:
			label = f"{label}: {filename}"
		text = f"[{label}]" + (f" {caption}" if caption else "")
		media = (part.get("id"), part.get("mime_type"), filename) if part.get("id") else None
		return kind, text, media
	if kind == "location":
		loc = m.get("location") or {}
		where = ", ".join(str(x) for x in (loc.get("name"), loc.get("address")) if x)
		text = f"[{_('Location')}] {loc.get('latitude')}, {loc.get('longitude')}"
		return kind, text + (f" ({where})" if where else ""), None
	if kind == "contacts":
		cards = []
		for c in m.get("contacts") or []:
			name = (c.get("name") or {}).get("formatted_name") or ""
			phones = ", ".join(p.get("phone") or "" for p in c.get("phones") or [] if p.get("phone"))
			cards.append(" ".join(x for x in (name, phones) if x))
		return kind, f"[{_('Contact card')}] " + "; ".join(cards), None
	if kind == "interactive":
		part = m.get("interactive") or {}
		reply = part.get("button_reply") or part.get("list_reply") or {}
		return kind, (reply.get("title") or "").strip(), None
	if kind == "button":
		return kind, ((m.get("button") or {}).get("text") or "").strip(), None
	return kind, "", None


def ticket_subject(text: str, name: str | None, number: str) -> str:
	first = next((line.strip() for line in (text or "").splitlines() if line.strip()), "")
	if first and not first.startswith("["):
		return first[:137] + "..." if len(first) > 140 else first
	return _("WhatsApp message from {0}").format(name or f"+{number}")[:140]


def message_html(text: str) -> str:
	"""The customer's words as the ticket feed shows them: escaped, with
	their line breaks."""
	return "<p>" + html.escape(text or "").replace("\n", "<br>") + "</p>"


class _ToText(HTMLParser):
	"""HTML from the reply editor to WhatsApp's plain text with *bold* and
	_italic_. Quoted history (blockquotes) is left out: on WhatsApp the
	conversation is already on screen."""

	BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre"}

	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.out, self.quote, self.lists, self.links = [], 0, [], []

	def handle_starttag(self, tag, attrs):
		if tag == "blockquote":
			self.quote += 1
		elif self.quote:
			return
		elif tag in ("strong", "b"):
			self.out.append("*")
		elif tag in ("em", "i"):
			self.out.append("_")
		elif tag in ("s", "del", "strike"):
			self.out.append("~")
		elif tag == "br":
			self.out.append("\n")
		elif tag == "a":
			self.links.append((dict(attrs).get("href") or "", len(self.out)))
		elif tag in ("ul", "ol"):
			self.lists.append([tag, 0])
		elif tag == "li":
			self.out.append("\n")
			if self.lists:
				self.lists[-1][1] += 1
				kind, n = self.lists[-1]
				self.out.append(f"{n}. " if kind == "ol" else "• ")
		elif tag in self.BLOCK:
			self.out.append("\n")

	def _close(self, marker):
		# An empty <strong></strong> leaves nothing, not a stray "**".
		if self.out and self.out[-1] == marker:
			self.out.pop()
		else:
			self.out.append(marker)

	def handle_endtag(self, tag):
		if tag == "blockquote":
			self.quote = max(0, self.quote - 1)
		elif self.quote:
			return
		elif tag in ("strong", "b"):
			self._close("*")
		elif tag in ("em", "i"):
			self._close("_")
		elif tag in ("s", "del", "strike"):
			self._close("~")
		elif tag == "a" and self.links:
			href, start = self.links.pop()
			if href.startswith(("http://", "https://")) and href not in "".join(self.out[start:]):
				self.out.append(f" ({href})")
		elif tag in ("ul", "ol"):
			if self.lists:
				self.lists.pop()
		elif tag in self.BLOCK and tag != "li":
			self.out.append("\n")

	def handle_data(self, data):
		if not self.quote:
			self.out.append(data)


def html_to_whatsapp(content: str) -> str:
	parser = _ToText()
	parser.feed(content or "")
	parser.close()
	text = "".join(parser.out).replace("\xa0", " ")
	text = re.sub(r"[ \t]+\n", "\n", text)
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()


def split_text(text: str, limit: int = MAX_TEXT) -> list:
	"""Text in pieces WhatsApp accepts, cut at a paragraph, line or word."""
	text = (text or "").strip()
	parts = []
	while len(text) > limit:
		cut = max(text.rfind("\n\n", 0, limit), text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
		if cut <= 0:
			cut = limit
		parts.append(text[:cut].strip())
		text = text[cut:].strip()
	if text:
		parts.append(text)
	return parts


def within_window(last_inbound, now, hours: int = WINDOW_HOURS) -> bool:
	return bool(last_inbound) and now - last_inbound < timedelta(hours=hours)


def template_text(text: str, limit: int = 900) -> str:
	"""A template parameter: one line, no tabs or runs of spaces (WhatsApp
	refuses those), short enough for its limit."""
	one = re.sub(r"\s+", " ", text or "").strip()
	return one if len(one) <= limit else one[: limit - 1].rstrip() + "…"


def check_windows(states: dict, now: float, limits) -> tuple:
	"""Fixed-window rate limit. `states` maps window seconds to
	{"start", "count"}. Returns (allowed, new states); a refused call does
	not count."""
	new = {}
	for seconds, limit in limits:
		state = states.get(seconds) or {}
		if not state or now - float(state.get("start") or 0) >= seconds:
			state = {"start": now, "count": 0}  # no window yet, or it ran out
		if int(state.get("count") or 0) >= limit:
			return False, states
		new[seconds] = {"start": state["start"], "count": int(state.get("count") or 0) + 1}
	return True, new


def render_ack(template: str | None, ticket: str, name: str | None) -> str:
	first = (name or "").split(" ")[0].strip()
	try:
		return (template or DEFAULT_ACK).format(ticket=ticket, name=f", {first}" if first else "")
	except (KeyError, IndexError, ValueError):
		return DEFAULT_ACK.format(ticket=ticket, name=f", {first}" if first else "")


# ---------------------------------------------------------------------------
# Settings and the Graph API
# ---------------------------------------------------------------------------


def settings():
	return frappe.get_cached_doc("HD WhatsApp Settings")


def is_ready(s) -> bool:
	return bool(
		cint(s.enabled)
		and s.phone_number_id
		and s.get_password("access_token", raise_exception=False)
	)


def _api(s, method: str, path: str, **kwargs) -> dict:
	token = s.get_password("access_token", raise_exception=False)
	url = f"{GRAPH}/{s.graph_version or DEFAULT_VERSION}/{path}"
	try:
		r = requests.request(
			method, url, headers={"Authorization": f"Bearer {token}"}, timeout=20, **kwargs
		)
	except requests.RequestException as e:
		raise WhatsAppError(_("Could not reach WhatsApp: {0}").format(e)) from e
	try:
		data = r.json()
	except ValueError:
		data = {}
	if r.status_code >= 400 or (isinstance(data, dict) and data.get("error")):
		err = (data or {}).get("error") or {}
		details = (err.get("error_data") or {}).get("details")
		message = err.get("message") or f"HTTP {r.status_code}"
		raise WhatsAppError(f"{message}" + (f" ({details})" if details else ""), err.get("code"))
	return data


def _send(s, payload: dict) -> str:
	data = _api(
		s,
		"POST",
		f"{s.phone_number_id}/messages",
		json={"messaging_product": "whatsapp", "recipient_type": "individual", **payload},
	)
	return ((data.get("messages") or [{}])[0]).get("id")


def _log(direction, wa_id, *, wamid=None, ticket=None, communication=None, kind="text",
		 body=None, status=None, error=None, contact_name=None) -> None:
	frappe.get_doc(
		{
			"doctype": "HD WhatsApp Message",
			"direction": direction,
			"wa_id": wa_id,
			"wamid": wamid,
			"ticket": ticket,
			"communication": communication,
			"message_type": kind,
			"body": (body or "")[:5000] or None,
			"status": status,
			"error": (error or "")[:1000] or None,
			"contact_name": contact_name,
		}
	).insert(ignore_permissions=True)


def send_text(s, to: str, text: str, *, ticket=None, communication=None) -> str:
	try:
		wamid = _send(s, {"to": to, "type": "text", "text": {"preview_url": False, "body": text}})
	except WhatsAppError as e:
		_log("Outgoing", to, ticket=ticket, communication=communication, body=text, status="Failed", error=str(e))
		raise
	_log("Outgoing", to, wamid=wamid, ticket=ticket, communication=communication, body=text, status="Sent")
	return wamid


def send_template(s, to: str, name: str, language: str, params=(), *, ticket=None, communication=None) -> str:
	template = {"name": name, "language": {"code": language or "en"}}
	if params:
		template["components"] = [
			{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}
		]
	body = f"[{_('Template')}: {name}] " + " | ".join(params)
	try:
		wamid = _send(s, {"to": to, "type": "template", "template": template})
	except WhatsAppError as e:
		_log("Outgoing", to, ticket=ticket, communication=communication, kind="template", body=body, status="Failed", error=str(e))
		raise
	_log("Outgoing", to, wamid=wamid, ticket=ticket, communication=communication, kind="template", body=body, status="Sent")
	return wamid


def send_file(s, to: str, file_name: str, *, ticket=None, communication=None) -> str:
	"""Upload one of our (private) files to WhatsApp and send it."""
	f = frappe.get_doc("File", file_name)
	content = f.get_content()
	if isinstance(content, str):
		content = content.encode()
	mime = mimetypes.guess_type(f.file_name or "")[0] or "application/octet-stream"
	kind = "image" if mime in ("image/jpeg", "image/png") else "document"
	label = f"[{_('Attachment')}: {f.file_name}]"
	try:
		media = _api(
			s,
			"POST",
			f"{s.phone_number_id}/media",
			data={"messaging_product": "whatsapp", "type": mime},
			files={"file": (f.file_name, content, mime)},
		)
		part = {"id": media.get("id")}
		if kind == "document":
			part["filename"] = f.file_name
		wamid = _send(s, {"to": to, "type": kind, kind: part})
	except WhatsAppError as e:
		_log("Outgoing", to, ticket=ticket, communication=communication, kind=kind, body=label, status="Failed", error=str(e))
		raise
	_log("Outgoing", to, wamid=wamid, ticket=ticket, communication=communication, kind=kind, body=label, status="Sent")
	return wamid


def _download(s, media_id: str):
	"""(content, mime) of an attachment the customer sent, or None."""
	meta = _api(s, "GET", media_id)
	if cint(meta.get("file_size")) > MAX_MEDIA_BYTES or not meta.get("url"):
		return None
	token = s.get_password("access_token", raise_exception=False)
	try:
		r = requests.get(meta["url"], headers={"Authorization": f"Bearer {token}"}, timeout=60)
	except requests.RequestException:
		return None
	if r.status_code != 200 or len(r.content) > MAX_MEDIA_BYTES:
		return None
	return r.content, (meta.get("mime_type") or "").split(";")[0].strip()


# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------


def _plain(text: str, status: int = 200) -> Response:
	return Response(text, status=status, mimetype="text/plain")


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def webhook():
	"""Meta's callback URL. GET is the one-time verification handshake; POST
	carries messages and delivery statuses."""
	s = settings()
	if frappe.request.method == "GET":
		args = frappe.request.args
		token = args.get("hub.verify_token") or ""
		if (
			args.get("hub.mode") == "subscribe"
			and s.verify_token
			and hmac.compare_digest(token.encode(), s.verify_token.encode())
		):
			return _plain(args.get("hub.challenge") or "")
		return _plain("Verification failed", 403)

	body = frappe.request.get_data() or b""
	secret = s.get_password("app_secret", raise_exception=False)
	if not verify_signature(secret, body, frappe.request.headers.get("X-Hub-Signature-256")):
		return _plain("Invalid signature", 403)
	if not cint(s.enabled):
		return _plain("Ignored: the WhatsApp channel is switched off")
	try:
		payload = json.loads(body)
	except ValueError:
		return _plain("Bad request", 400)
	frappe.enqueue("helpdesk.integrations.whatsapp.process", queue="short", payload=payload)
	return _plain("OK")


def process(payload: dict) -> None:
	"""Background job: everything one webhook call delivered, one message at
	a time, each in its own transaction."""
	frappe.set_user("Administrator")
	s = settings()
	for entry in payload.get("entry") or []:
		for change in entry.get("changes") or []:
			if change.get("field") != "messages":
				continue
			value = change.get("value") or {}
			meta = value.get("metadata") or {}
			if s.phone_number_id and str(meta.get("phone_number_id")) != str(s.phone_number_id):
				continue  # another number on the same Meta app
			own = digits(meta.get("display_phone_number"))
			if own and own != digits(s.display_phone_number):
				frappe.db.set_single_value("HD WhatsApp Settings", "display_phone_number", own)
			names = {
				digits(c.get("wa_id")): (c.get("profile") or {}).get("name")
				for c in value.get("contacts") or []
			}
			for m in value.get("messages") or []:
				try:
					_receive(s, m, names.get(digits(m.get("from"))), own)
					frappe.db.commit()
				except Exception:
					frappe.db.rollback()
					frappe.log_error(title=f"WhatsApp: could not take in message {m.get('id')}")
			for status in value.get("statuses") or []:
				try:
					_delivery(status)
					frappe.db.commit()
				except Exception:
					frappe.db.rollback()
					frappe.log_error(title=f"WhatsApp: could not record status for {status.get('id')}")


def _contact_for(wa_id: str, name: str | None):
	"""The Contact with this number (matched on its last nine digits, so
	"0712 345 678" finds 254712345678), or a new one."""
	tail = wa_id[-9:]
	phone = frappe.qb.DocType("Contact Phone")
	normalized = phone.phone
	for ch in (" ", "-", "(", ")", "+", "."):
		normalized = Replace(normalized, ch, "")
	rows = (
		frappe.qb.from_(phone)
		.select(phone.parent)
		.where(phone.parenttype == "Contact")
		.where(normalized.like(f"%{tail}"))
		.limit(1)
		.run()
	)
	if rows:
		return frappe.get_doc("Contact", rows[0][0])
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": (name or f"+{wa_id}")[:140],
			"phone_nos": [{"phone": f"+{wa_id}", "is_primary_mobile_no": 1}],
		}
	)
	contact.insert(ignore_permissions=True)
	return contact


def _ticket_for(s, wa_id: str):
	"""The sender's open ticket, or one resolved within the reopen window."""
	rows = frappe.get_all(
		"HD Ticket",
		filters={"whatsapp_number": wa_id},
		fields=["name", "status_category", "modified"],
		order_by="creation desc",
		limit_page_length=1,
	)
	if not rows:
		return None
	t = rows[0]
	if t.status_category != "Resolved":
		return t.name
	hours = cint(s.reopen_window_hours) if s.reopen_window_hours is not None else 72
	if hours and get_datetime(t.modified) > add_to_date(now_datetime(), hours=-hours):
		return t.name
	return None


def _receive(s, m: dict, profile_name: str | None, own_number: str) -> None:
	wamid = m.get("id")
	wa_id = digits(m.get("from"))
	if not wamid or not wa_id or frappe.db.exists("HD WhatsApp Message", {"wamid": wamid}):
		return  # Meta redelivers until it gets a 200; once is enough
	kind, text, media = parse_message(m)
	if wa_id == own_number or kind in SILENT_TYPES or not (text or media):
		_log("Incoming", wa_id, wamid=wamid, kind=kind, body=text, status="Received", contact_name=profile_name)
		return

	contact = _contact_for(wa_id, profile_name)
	ticket_name = _ticket_for(s, wa_id)
	is_new = not ticket_name
	if is_new:
		ticket = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": ticket_subject(text, profile_name, wa_id),
				"whatsapp_number": wa_id,
				"contact": contact.name,
				"agent_group": s.default_team or None,
			}
		)
		ticket.insert(ignore_permissions=True)
	else:
		ticket = frappe.get_doc("HD Ticket", ticket_name)

	sent_at = datetime.fromtimestamp(cint(m.get("timestamp")) or time.time())
	c = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Chat",
			"sent_or_received": "Received",
			"email_status": "Open",
			"subject": f"Re: {ticket.subject}",
			"sender_full_name": profile_name or contact.get("full_name") or f"+{wa_id}",
			"phone_no": f"+{wa_id}",
			"content": message_html(text),
			"status": "Linked",
			"reference_doctype": "HD Ticket",
			"reference_name": ticket.name,
			"communication_date": sent_at,
		}
	)
	c.insert(ignore_permissions=True)
	if media:
		_attach(s, ticket, c.name, *media)
	_log(
		"Incoming", wa_id, wamid=wamid, ticket=ticket.name, communication=c.name, kind=kind,
		body=text, status="Received", contact_name=profile_name,
	)
	if is_new:
		_acknowledge(s, ticket, wa_id, profile_name)


def _attach(s, ticket, communication: str, media_id, mime, filename) -> None:
	try:
		got = _download(s, media_id)
	except WhatsAppError:
		got = None
	if not got:
		frappe.log_error(title=f"WhatsApp: could not fetch an attachment for {ticket.name}")
		return
	content, mime = got[0], got[1] or mime or "application/octet-stream"
	if not filename:
		ext = mimetypes.guess_extension(mime) or ""
		filename = f"whatsapp-{media_id}{ext}"
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Communication",
			"attached_to_name": communication,
		}
	)
	f.save(ignore_permissions=True)
	ticket.attach_file_with_doc("HD Ticket", ticket.name, f.file_url)


def _rate_limited(key: str, limits) -> bool:
	"""Per-number circuit breaker for automatic messages. A cache failure
	never blocks a message."""
	try:
		cache = frappe.cache()
		states = {sec: cache.get_value(f"{key}:{sec}", expires=True) for sec, _l in limits}
		allowed, new = check_windows(
			{k: v for k, v in states.items() if isinstance(v, dict)}, time.time(), limits
		)
		if not allowed:
			return True
		for sec, state in new.items():
			cache.set_value(f"{key}:{sec}", state, expires_in_sec=sec)
	except Exception:
		return False
	return False


def _acknowledge(s, ticket, wa_id: str, name: str | None) -> None:
	"""The new-ticket acknowledgement, the only automatic WhatsApp message.
	Checked last against the per-number limit, so the budget is only spent
	when a message actually goes out."""
	if not cint(s.send_acknowledgement) or not is_ready(s):
		return
	if _rate_limited(f"hd-wa-ack:{wa_id}", ACK_LIMITS):
		frappe.log_error(
			title=f"WhatsApp: acknowledgement to +{wa_id} suppressed (loop guard)",
			message=f"Ticket {ticket.name}: the per-number limit was reached.",
		)
		return
	try:
		send_text(s, wa_id, render_ack(s.acknowledgement_message, ticket.name, name), ticket=ticket.name)
	except WhatsAppError:
		frappe.log_error(title=f"WhatsApp: acknowledgement failed for {ticket.name}")


def _delivery(status: dict) -> None:
	"""A delivery status for something we sent: sent, delivered, read or
	failed. Never moves backwards (a late "delivered" after "read")."""
	row = frappe.db.get_value(
		"HD WhatsApp Message", {"wamid": status.get("id")}, ["name", "status", "communication"], as_dict=True
	)
	if not row:
		return
	label = {"sent": "Sent", "delivered": "Delivered", "read": "Read", "failed": "Failed"}.get(status.get("status"))
	if not label:
		return
	if label != "Failed" and STATUS_RANK.get(label, 0) <= STATUS_RANK.get(row.status, 0):
		return
	error = None
	if label == "Failed":
		e = (status.get("errors") or [{}])[0]
		error = e.get("message") or e.get("title") or _("Not delivered")
		details = (e.get("error_data") or {}).get("details")
		if details:
			error = f"{error} ({details})"
	frappe.db.set_value("HD WhatsApp Message", row.name, {"status": label, "error": error})
	# Only a WhatsApp-only reply's badge: an emailed one has email's verdict.
	if (
		row.communication
		and frappe.db.get_value("Communication", row.communication, "communication_medium") == "Chat"
	):
		frappe.db.set_value(
			"Communication",
			row.communication,
			"delivery_status",
			{"Read": "Read", "Failed": "Error"}.get(label, "Sent"),
			update_modified=False,
		)


# ---------------------------------------------------------------------------
# Outbound: an agent's reply
# ---------------------------------------------------------------------------


def last_inbound(wa_id: str):
	when = frappe.db.get_value(
		"HD WhatsApp Message",
		{"wa_id": wa_id, "direction": "Incoming"},
		"creation",
		order_by="creation desc",
	)
	return get_datetime(when) if when else None


def send_agent_reply(ticket, communication, message: str, attachments=(), email_too=False) -> dict:
	"""Called by HD Ticket.reply_via_agent for a WhatsApp ticket, after the
	reply is saved. `email_too`: the agent also addressed someone by email,
	so the reply stays an email in the feed. Never raises: the outcome is
	returned for the agent's toast."""
	to = digits(ticket.get("whatsapp_number"))
	out = {"whatsapp_to": f"+{to}"}
	s = settings()
	if not is_ready(s):
		return {**out, "whatsapp": "failed", "whatsapp_reason": _("WhatsApp is not set up: Settings > WhatsApp.")}
	text = html_to_whatsapp(message)
	comm = communication.name
	try:
		if within_window(last_inbound(to), now_datetime()):
			for part in split_text(text):
				send_text(s, to, part, ticket=ticket.name, communication=comm)
			for file_name in attachments or []:
				send_file(s, to, file_name, ticket=ticket.name, communication=comm)
		elif s.template_name:
			send_template(
				s, to, s.template_name, s.template_language,
				[ticket.name, template_text(text) or "-"],
				ticket=ticket.name, communication=comm,
			)
			out["whatsapp_note"] = _(
				"More than 24 hours since the customer last wrote, so the reply went as the approved template."
			)
		else:
			return {
				**out,
				"whatsapp": "failed",
				"whatsapp_reason": _(
					"The customer last wrote more than 24 hours ago. WhatsApp then only allows an "
					"approved template message: add one in Settings > WhatsApp, or reach them another way."
				),
			}
	except WhatsAppError as e:
		reason = str(e)
		if e.code == 131047:
			reason = _("WhatsApp's 24-hour reply window has closed: {0}").format(reason)
		if not email_too:
			frappe.db.set_value("Communication", comm, "delivery_status", "Error", update_modified=False)
		return {**out, "whatsapp": "failed", "whatsapp_reason": reason}
	if not email_too:
		frappe.db.set_value(
			"Communication",
			comm,
			{"communication_medium": "Chat", "phone_no": f"+{to}", "delivery_status": "Sent"},
			update_modified=False,
		)
	return {**out, "whatsapp": "sent"}
