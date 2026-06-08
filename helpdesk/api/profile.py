# Customer-portal profile + notification preferences.
#
# All endpoints act on the *current* session user's own records only, so writes
# use frappe.db.set_value / ignore_permissions safely without granting a customer
# broad access to the User / Contact / preference doctypes.

import frappe
from frappe import _
from frappe.utils import cint


def _get_prefs(user: str) -> frappe._dict:
	row = frappe.db.get_value(
		"HD Portal Preference",
		user,
		["email_updates", "product_announcements"],
		as_dict=True,
	)
	if not row:
		return frappe._dict(email_updates=1, product_announcements=0)
	return frappe._dict(
		email_updates=cint(row.email_updates),
		product_announcements=cint(row.product_announcements),
	)


def wants_email_updates(user: str) -> bool:
	"""Whether `user` has opted in to ticket-update emails (default: yes)."""
	if not user or user == "Guest":
		return True
	return bool(_get_prefs(user).email_updates)


def _assert_user() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return user


@frappe.whitelist()
def get_profile() -> dict:
	"""Current user's portal profile + notification preferences."""
	user = _assert_user()
	u = (
		frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True)
		or frappe._dict()
	)
	contact = (
		frappe.db.get_value(
			"Contact", {"email_id": user}, ["name", "mobile_no", "phone"], as_dict=True
		)
		or frappe._dict()
	)
	prefs = _get_prefs(user)
	return {
		"full_name": u.full_name or "",
		"email": user,
		"image": u.user_image or "",
		"phone": contact.mobile_no or contact.phone or "",
		"email_updates": prefs.email_updates,
		"product_announcements": prefs.product_announcements,
	}


@frappe.whitelist()
def update_profile(
	full_name: str | None = None,
	phone: str | None = None,
	image: str | None = None,
) -> dict:
	"""Update the current user's display name, phone, and/or avatar."""
	user = _assert_user()

	if full_name is not None:
		full_name = full_name.strip()
		if full_name:
			parts = full_name.split(" ", 1)
			frappe.db.set_value(
				"User",
				user,
				{
					"first_name": parts[0],
					"last_name": parts[1] if len(parts) > 1 else "",
					"full_name": full_name,
				},
			)

	if image is not None:
		frappe.db.set_value("User", user, "user_image", image or None)

	if phone is not None:
		contact = frappe.db.get_value("Contact", {"email_id": user}, "name")
		if contact:
			frappe.db.set_value("Contact", contact, "mobile_no", phone or None)

	return get_profile()


@frappe.whitelist()
def update_preferences(
	email_updates: int | None = None,
	product_announcements: int | None = None,
) -> dict:
	"""Upsert the current user's notification preferences."""
	user = _assert_user()
	if frappe.db.exists("HD Portal Preference", user):
		doc = frappe.get_doc("HD Portal Preference", user)
	else:
		doc = frappe.get_doc({"doctype": "HD Portal Preference", "user": user})

	if email_updates is not None:
		doc.email_updates = cint(email_updates)
	if product_announcements is not None:
		doc.product_announcements = cint(product_announcements)
	doc.save(ignore_permissions=True)
	return _get_prefs(user)
