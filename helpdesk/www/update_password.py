import frappe

no_cache = 1


def get_context(context):
	# With no reset key this page changes a signed-in user's password. A
	# visitor who isn't signed in can't use that form - they want a reset
	# email, so send them to the request instead.
	if frappe.session.user == "Guest" and not frappe.form_dict.get("key"):
		frappe.local.flags.redirect_location = "/login?forgot=1"
		raise frappe.Redirect

	context.title = "Set Password — CyveTech Support Desk"
