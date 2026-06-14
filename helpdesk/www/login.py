import frappe

# Disable page caching so the login form is always fresh.
no_cache = 1


def get_context(context):
	# Already-authenticated users have nothing to do on the login page.
	if frappe.session.user != "Guest":
		redirect_to = frappe.local.request.args.get("redirect-to") or "/helpdesk"
		frappe.local.flags.redirect_location = redirect_to
		raise frappe.Redirect

	context.title = "Sign In — CyveTech Support Desk"
