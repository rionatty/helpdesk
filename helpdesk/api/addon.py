# Add-ons API.
#
# Agents manage add-ons (deployed apps/modules per customer). Customers view
# their own company's add-ons (read-only). Access is checked explicitly, then
# queries run with ignore_permissions.

import frappe
from frappe import _

from helpdesk.utils import get_customer, is_agent

ADDON_FIELDS = [
	"name",
	"addon_name",
	"customer",
	"status",
	"version",
	"activated_on",
	"renewal_date",
	"notes",
	"modified",
]

WRITABLE = {
	"addon_name",
	"customer",
	"status",
	"version",
	"activated_on",
	"renewal_date",
	"notes",
}


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can manage add-ons"), frappe.PermissionError)


@frappe.whitelist()
def get_addons(customer: str | None = None) -> list:
	"""List add-ons. Agents see all (optionally by customer); customers see
	only their company's add-ons."""
	filters: dict = {}
	if customer:
		filters["customer"] = customer
	if not is_agent():
		companies = get_customer(frappe.session.user)
		if not companies:
			return []
		filters["customer"] = ["in", companies]
	return frappe.get_all(
		"HD Addon",
		filters=filters,
		fields=ADDON_FIELDS,
		order_by="modified desc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def create_addon(
	addon_name: str,
	customer: str,
	status: str = "Active",
	version: str | None = None,
	activated_on: str | None = None,
	renewal_date: str | None = None,
	notes: str | None = None,
) -> str:
	"""Create an add-on. Agents only."""
	_assert_agent()
	if not (addon_name or "").strip():
		frappe.throw(_("Add-on name is required"))
	if not customer:
		frappe.throw(_("Customer is required"))
	doc = frappe.get_doc(
		{
			"doctype": "HD Addon",
			"addon_name": addon_name.strip(),
			"customer": customer,
			"status": status or "Active",
			"version": version,
			"activated_on": activated_on,
			"renewal_date": renewal_date,
			"notes": notes,
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_addon(name: str, **fields) -> bool:
	"""Update writable add-on fields. Agents only."""
	_assert_agent()
	doc = frappe.get_doc("HD Addon", name)
	for key, value in fields.items():
		if key in WRITABLE:
			doc.set(key, value)
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_addon(name: str) -> bool:
	"""Delete an add-on. Agents only."""
	_assert_agent()
	frappe.delete_doc("HD Addon", name, ignore_permissions=True)
	return True
