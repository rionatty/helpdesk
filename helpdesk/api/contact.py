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


@frappe.whitelist()
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


@frappe.whitelist()
def search_assignable(txt: str = "") -> list[dict]:
    """Search Frappe Users then Contacts for HD Customer assignment.

    Users come first; Contacts with no matching User account fill the rest.
    """
    results: list[dict] = []
    seen_emails: set[str] = set()

    # ── Frappe Users ──────────────────────────────────────────────────────────
    u_or: list = []
    if txt:
        u_or = [
            ["User", "full_name", "like", f"%{txt}%"],
            ["User", "name", "like", f"%{txt}%"],
        ]
    for u in frappe.get_list(
        "User",
        filters={"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]},
        or_filters=u_or or None,
        fields=["name", "full_name", "user_image"],
        limit_page_length=10,
        order_by="full_name",
        ignore_permissions=True,
    ):
        seen_emails.add(u.name)
        results.append(
            {
                "name": u.name,
                "full_name": u.full_name or u.name,
                "email_id": u.name,
                "image": u.user_image,
                "record_type": "user",
            }
        )

    # ── Contacts not already represented by a User above ─────────────────────
    remaining = max(0, 10 - len(results))
    if remaining:
        c_or: list = []
        if txt:
            c_or = [
                ["Contact", "full_name", "like", f"%{txt}%"],
                ["Contact", "email_id", "like", f"%{txt}%"],
            ]
        for c in frappe.get_list(
            "Contact",
            filters=[["Contact", "email_id", "is", "set"]],
            or_filters=c_or or None,
            fields=["name", "full_name", "email_id", "image"],
            limit_page_length=remaining,
            order_by="full_name",
        ):
            if c.email_id not in seen_emails:
                seen_emails.add(c.email_id)
                results.append(
                    {
                        "name": c.name,
                        "full_name": c.full_name or c.email_id,
                        "email_id": c.email_id,
                        "image": c.image,
                        "record_type": "contact",
                    }
                )

    return results


@frappe.whitelist()
def add_assignable_to_customer(identifier: str, record_type: str, customer: str) -> None:
    """Link a User or Contact to an HD Customer.

    For a User, finds or creates a Contact record then links it.
    For a Contact, links it directly.
    """
    if record_type == "user":
        _link_user_to_customer(identifier, customer)
    else:
        add_contact_to_customer(identifier, customer)


def _link_user_to_customer(user_email: str, customer: str) -> None:
    contact_name = frappe.db.get_value("Contact", {"email_id": user_email}, "name")
    if not contact_name:
        u = frappe.get_doc("User", user_email)
        contact = frappe.new_doc("Contact")
        contact.first_name = u.first_name or u.full_name or user_email.split("@")[0]
        if u.last_name:
            contact.last_name = u.last_name
        contact.user = user_email
        contact.append("email_ids", {"email_id": user_email, "is_primary": 1})
        contact.append("links", {"link_doctype": "HD Customer", "link_name": customer})
        contact.insert()
        return
    add_contact_to_customer(contact_name, customer)


@frappe.whitelist()
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


@frappe.whitelist()
def add_contact_to_customer(contact: str, customer: str) -> None:
    """Link a Contact to an HD Customer via a Dynamic Link (idempotent)."""
    doc = frappe.get_doc("Contact", contact)
    for link in doc.links:
        if link.link_doctype == "HD Customer" and link.link_name == customer:
            return
    doc.append("links", {"link_doctype": "HD Customer", "link_name": customer})
    doc.save()


@frappe.whitelist()
def remove_contact_from_customer(contact: str, customer: str) -> None:
    """Remove the HD Customer Dynamic Link from a Contact."""
    doc = frappe.get_doc("Contact", contact)
    doc.links = [
        lnk
        for lnk in doc.links
        if not (lnk.link_doctype == "HD Customer" and lnk.link_name == customer)
    ]
    doc.save()
