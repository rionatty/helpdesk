from typing import Literal

import frappe

from helpdesk.utils import get_customer


@frappe.whitelist(methods=["GET"])
def get_my_companies() -> list[dict]:
	"""HD Customers (companies) the current user belongs to, via their Contact.

	Used by the customer portal to offer a company-wide ticket view. The ticket
	permission query already allows a contact to read tickets where
	`customer` is one of these, so no extra access is granted here.
	"""
	names = get_customer(frappe.session.user)
	if not names:
		return []
	return frappe.get_all(
		"HD Customer",
		filters={"name": ["in", names]},
		fields=["name"],
	)


@frappe.whitelist(methods=["GET"])
def search_contacts(
    txt: str,
) -> list[dict[Literal["full_name", "name", "email_id"], str]]:
    doctype = "Contact"
    or_filters: list[list[str]] = []
    search_fields = ["full_name", "email_id", "name"]
    if txt:
        for field in search_fields:
            or_filters.append([doctype, field, "like", f"%{txt}%"])
    return frappe.get_list(
        doctype,
        filters=[[doctype, "email_id", "is", "set"]],
        fields=search_fields,
        or_filters=or_filters,
        limit_start=0,
        limit_page_length=10,
        order_by="email_id, full_name, name",
        ignore_permissions=False,
        strict=False,
    )
