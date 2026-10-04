# Settings API for the Pumble integration (helpdesk/integrations/pumble.py).
#
# Manager-only. A channel's webhook URL is a secret - anyone holding it can
# post into the channel - so it is stored in a Password field and never sent
# back to the browser; the list only says whether one is set.

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.password import get_decrypted_password

from helpdesk.integrations import pumble

CHECKS = (
	"enabled",
	"on_new_ticket",
	"on_customer_reply",
	"on_sla_breach",
	"on_ticket_resolved",
	"on_project_activity",
)
EDITABLE = ("channel_name", *CHECKS, "project", "customer", "email_account")


def _manager_only() -> None:
	frappe.only_for(["Agent Manager", "System Manager"])


@frappe.whitelist()
def get_channels() -> list:
	_manager_only()
	rows = frappe.get_all(
		"HD Pumble Channel", fields=["name", *EDITABLE], order_by="creation asc"
	)
	for row in rows:
		row["has_webhook"] = bool(
			get_decrypted_password(
				"HD Pumble Channel", row.name, "webhook_url", raise_exception=False
			)
		)
		row["project_name"] = (
			frappe.db.get_value("HD Project", row.project, "project_name")
			if row.project
			else None
		)
	return rows


@frappe.whitelist()
def get_scope_options() -> dict:
	"""What a channel can be narrowed to. Read with ignore_permissions so an
	Agent Manager without Email Account access can still pick an inbox."""
	_manager_only()
	return {
		"projects": frappe.get_all(
			"HD Project",
			fields=["name", "project_name"],
			order_by="project_name asc",
			limit_page_length=0,
		),
		"customers": frappe.get_all(
			"HD Customer", pluck="name", order_by="name asc", limit_page_length=0
		),
		"inboxes": frappe.get_all(
			"Email Account",
			filters={"enable_incoming": 1},
			fields=["name", "email_id"],
			order_by="email_id asc",
			ignore_permissions=True,
		),
	}


@frappe.whitelist()
def save_channel(data) -> str:
	_manager_only()
	data = frappe._dict(frappe.parse_json(data) if isinstance(data, str) else (data or {}))
	name = data.get("name")
	doc = (
		frappe.get_doc("HD Pumble Channel", name)
		if name
		else frappe.new_doc("HD Pumble Channel")
	)
	for field in EDITABLE:
		if field not in data:
			continue
		value = data.get(field)
		doc.set(field, (1 if cint(value) else 0) if field in CHECKS else (value or None))
	if not (doc.channel_name or "").strip():
		frappe.throw(_("Give the channel a name"))

	url = (data.get("webhook_url") or "").strip()
	if url:
		if not pumble.valid_webhook(url):
			frappe.throw(
				_("That isn't a Pumble webhook URL. It should start with {0}").format(
					pumble.WEBHOOK_PREFIX
				)
			)
		doc.webhook_url = url
	elif doc.is_new():
		frappe.throw(_("Paste the channel's webhook URL from Pumble"))
	# Left blank on an existing channel: the saved secret is kept as-is.

	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def delete_channel(name: str) -> bool:
	_manager_only()
	# The delivery history links to the channel; it goes with it.
	frappe.db.delete("HD Pumble Log", {"channel": name})
	frappe.delete_doc("HD Pumble Channel", name, ignore_permissions=True)
	return True


@frappe.whitelist()
def send_test(name: str) -> dict:
	"""Post a test message right now (not queued), so the manager sees at once
	whether the webhook works."""
	_manager_only()
	doc = frappe.get_doc("HD Pumble Channel", name)
	url = doc.get_password("webhook_url", raise_exception=False)
	text = pumble.test_message()
	error = (
		pumble.post(url, text)
		if pumble.valid_webhook(url)
		else _("No valid webhook URL is saved for this channel")
	)
	pumble.log_delivery(name, "test", text, error)
	return {"ok": not error, "error": error}


@frappe.whitelist()
def get_log(limit: int = 25) -> list:
	_manager_only()
	return frappe.get_all(
		"HD Pumble Log",
		fields=["name", "creation", "channel", "event", "status", "error"],
		order_by="creation desc",
		limit_page_length=max(1, min(cint(limit) or 25, 100)),
	)
