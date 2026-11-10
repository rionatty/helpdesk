"""A new user's "set your password" link - in the welcome email, and the one an
accepted invitation sends them to - is a password-reset link, so it shares
the reset link's lifetime. Frappe's default is 20 minutes: a new colleague
who opens their welcome email later that morning finds it already expired.

Raise it to 24 hours, but only while it is still Frappe's default, so a
lifetime someone chose on purpose is left alone. An expired link explains
itself and offers a fresh one, so 24 hours is a safe middle.
"""

import frappe
from frappe.utils import cint

FRAPPE_DEFAULT = 1200  # seconds
ONE_DAY = 24 * 60 * 60


def execute():
	# Only the untouched default. 0 or unset means links never expire, which
	# is a choice too, and must not be shortened.
	current = frappe.db.get_single_value(
		"System Settings", "reset_password_link_expiry_duration"
	)
	if cint(current) == FRAPPE_DEFAULT:
		frappe.db.set_single_value(
			"System Settings", "reset_password_link_expiry_duration", ONE_DAY
		)
