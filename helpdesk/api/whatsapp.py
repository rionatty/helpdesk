# Copyright (c) 2026, rionatty and contributors
# Settings API for the WhatsApp channel (helpdesk/integrations/whatsapp.py).
#
# Manager-only. The access token and the app secret are secrets: they are
# stored in Password fields and never sent back to the browser. The form only
# learns whether each one is set.

import re
import secrets

import frappe
from frappe import _
from frappe.utils import cint, get_url

from helpdesk.integrations import whatsapp

FIELDS = (
	"enabled",
	"phone_number_id",
	"business_account_id",
	"graph_version",
	"default_team",
	"reopen_window_hours",
	"send_acknowledgement",
	"acknowledgement_message",
	"template_name",
	"template_language",
)
SECRETS = ("access_token", "app_secret")
WEBHOOK_PATH = "/api/method/helpdesk.integrations.whatsapp.webhook"


def _manager_only() -> None:
	frappe.only_for(["Agent Manager", "System Manager"])


def _settings():
	s = frappe.get_single("HD WhatsApp Settings")
	if not s.verify_token:
		s.verify_token = secrets.token_urlsafe(24)
		s.save(ignore_permissions=True)
	return s


def _has(s, field: str) -> bool:
	return bool(s.get_password(field, raise_exception=False))


@frappe.whitelist()
def get_settings() -> dict:
	_manager_only()
	s = _settings()
	out = {f: s.get(f) for f in FIELDS}
	out.update({f"has_{f}": _has(s, f) for f in SECRETS})
	out.update(
		verify_token=s.verify_token,
		display_phone_number=s.display_phone_number,
		webhook_url=get_url(WEBHOOK_PATH),
		teams=frappe.get_all("HD Team", pluck="name", order_by="name asc"),
		ready=whatsapp.is_ready(s),
	)
	return out


@frappe.whitelist()
def save_settings(data) -> bool:
	_manager_only()
	data = frappe._dict(frappe.parse_json(data) if isinstance(data, str) else (data or {}))
	s = _settings()
	for field in FIELDS:
		if field in data:
			value = data.get(field)
			s.set(field, value.strip() if isinstance(value, str) else value)
	new_secrets = {f: (data.get(f) or "").strip() for f in SECRETS}
	for field, value in new_secrets.items():
		if value:
			s.set(field, value)
	s.phone_number_id = re.sub(r"\D", "", s.phone_number_id or "") or None
	s.graph_version = (s.graph_version or whatsapp.DEFAULT_VERSION).strip()
	if not re.fullmatch(r"v\d+\.\d+", s.graph_version):
		frappe.throw(_("The Graph API version looks like v23.0"))
	s.reopen_window_hours = max(0, cint(s.reopen_window_hours))
	if cint(s.enabled):
		missing = [] if s.phone_number_id else [_("Phone number ID")]
		for field, label in (("access_token", _("Access token")), ("app_secret", _("App secret"))):
			if not new_secrets[field] and not _has(s, field):
				missing.append(label)
		if missing:
			frappe.throw(_("To switch WhatsApp on, fill in: {0}").format(", ".join(missing)))
	s.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def new_verify_token() -> str:
	"""A fresh verify token. Meta keeps working with the old one until the
	webhook is verified again."""
	_manager_only()
	s = frappe.get_single("HD WhatsApp Settings")
	s.verify_token = secrets.token_urlsafe(24)
	s.save(ignore_permissions=True)
	return s.verify_token


@frappe.whitelist()
def send_test(to: str) -> str:
	"""Send Meta's own hello_world template. Every new WhatsApp account has
	it, and being a template it arrives whether or not the number has
	written to us. Works before the channel is switched on."""
	_manager_only()
	s = whatsapp.settings()
	if not s.phone_number_id or not _has(s, "access_token"):
		frappe.throw(_("Save the phone number ID and the access token first"))
	number = re.sub(r"\D", "", to or "")
	if len(number) < 8:
		frappe.throw(_("Enter the number with its country code, e.g. 254712345678"))
	try:
		return whatsapp.send_template(s, number, "hello_world", "en_US")
	except whatsapp.WhatsAppError as e:
		frappe.throw(_("WhatsApp said: {0}").format(e))


@frappe.whitelist()
def get_log(limit: int = 50) -> list:
	_manager_only()
	return frappe.get_all(
		"HD WhatsApp Message",
		fields=[
			"name", "creation", "direction", "wa_id", "contact_name", "message_type",
			"status", "ticket", "body", "error",
		],
		order_by="creation desc",
		limit_page_length=max(1, min(cint(limit) or 50, 200)),
	)
