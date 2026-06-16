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


@frappe.whitelist(methods=["GET"])
def get_customer_contacts(customer: str) -> list[dict]:
    """Return all Contacts that have a Dynamic Link to the given HD Customer."""
    parent_names = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "link_doctype": "HD Customer",
            "link_name": customer,
        },
        pluck="parent",
    )
    if not parent_names:
        return []
    return frappe.get_all(
        "Contact",
        filters={"name": ["in", parent_names]},
        fields=["name", "full_name", "email_id", "image", "user"],
    )


@frappe.whitelist(methods=["POST"])
def add_contact_to_customer(contact: str, customer: str) -> None:
    """Link a Contact to an HD Customer via a Dynamic Link (idempotent)."""
    doc = frappe.get_doc("Contact", contact)
    for link in doc.links:
        if link.link_doctype == "HD Customer" and link.link_name == customer:
            return
    doc.append("links", {"link_doctype": "HD Customer", "link_name": customer})
    doc.save()


@frappe.whitelist(methods=["POST"])
def remove_contact_from_customer(contact: str, customer: str) -> None:
    """Remove the HD Customer Dynamic Link from a Contact."""
    doc = frappe.get_doc("Contact", contact)
    doc.links = [
        lnk
        for lnk in doc.links
        if not (lnk.link_doctype == "HD Customer" and lnk.link_name == customer)
    ]
    doc.save()
