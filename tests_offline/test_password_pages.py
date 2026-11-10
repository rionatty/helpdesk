"""The helpdesk's own sign-in and set-password pages (helpdesk/www), tested
without a bench.

Password reset was broken because "Forgot password?" pointed at
/update-password with no reset key, so nobody could ask for a reset email.
These pin the fix: the login page asks Frappe to email a link, and the
set-password page sends a visitor who has no key to that request rather than
showing a "current password" form they cannot use.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

WWW = Path(__file__).resolve().parents[1] / "helpdesk/www"


class Redirect(Exception):
	pass


def _load_update_password(user: str, key: str | None):
	frappe = types.ModuleType("frappe")
	frappe.session = types.SimpleNamespace(user=user)
	frappe.form_dict = {"key": key} if key else {}
	frappe.local = types.SimpleNamespace(flags=types.SimpleNamespace(redirect_location=None))
	frappe.Redirect = Redirect
	with mock.patch.dict(sys.modules, {"frappe": frappe}):
		spec = importlib.util.spec_from_file_location(
			"update_password_page", WWW / "update_password.py"
		)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	return module, frappe


def context_for(user: str, key: str | None):
	module, frappe = _load_update_password(user, key)
	context = types.SimpleNamespace()
	try:
		module.get_context(context)
	except Redirect:
		return None, frappe.local.flags.redirect_location
	return context, None


class SetPasswordPage(unittest.TestCase):
	def test_a_visitor_without_a_key_is_sent_to_the_reset_request(self):
		context, redirect = context_for("Guest", None)
		self.assertIsNone(context)
		self.assertEqual(redirect, "/login?forgot=1")

	def test_a_visitor_with_a_key_from_the_email_gets_the_form(self):
		context, redirect = context_for("Guest", "abc123")
		self.assertIsNone(redirect)
		self.assertIn("Set Password", context.title)

	def test_a_signed_in_user_can_still_change_their_password(self):
		context, redirect = context_for("agent@cyvetech.com", None)
		self.assertIsNone(redirect)
		self.assertIn("Set Password", context.title)


class LoginPage(unittest.TestCase):
	html = (WWW / "login.html").read_text(encoding="utf-8")

	def test_forgot_password_no_longer_points_at_a_keyless_set_password_page(self):
		self.assertNotIn('href="/update-password"', self.html)

	def test_forgot_password_asks_frappe_to_email_a_reset_link(self):
		self.assertIn("/api/method/frappe.core.doctype.user.user.reset_password", self.html)
		# Frappe's reset_password takes the address as `user`.
		self.assertIn("'user=' + encodeURIComponent(email)", self.html)

	def test_the_request_panel_can_be_linked_to_directly(self):
		self.assertIn('id="forgot-form"', self.html)
		self.assertIn("get('forgot')", self.html)


class SetPasswordScript(unittest.TestCase):
	html = (WWW / "update-password.html").read_text(encoding="utf-8")

	def test_the_reason_for_a_dead_link_is_shown(self):
		# HTTP 410 carries the reason in `message`, not _server_messages.
		self.assertIn("typeof data.message === 'string'", self.html)
		self.assertIn("res.status === 410", self.html)

	def test_after_a_reset_people_land_in_the_helpdesk(self):
		# Frappe answers "/desk" for agents; only helpdesk paths are followed.
		self.assertIn(r"/^\/helpdesk(\/|\?|#|$)/.test(p)", self.html)
		self.assertIn("helpdeskPath(params.get('redirect_to')) || '/helpdesk'", self.html)


class CsrfToken(unittest.TestCase):
	"""A signed-in browser must send the real token, or Frappe answers
	"Invalid Request". Frappe sets no CSRF cookie; it fills in
	frappe.csrf_token where a rendered page says <!-- csrf_token -->."""

	def test_both_pages_ask_frappe_for_the_token_and_use_it(self):
		for page in ("login.html", "update-password.html"):
			html = (WWW / page).read_text(encoding="utf-8")
			with self.subTest(page=page):
				self.assertEqual(html.count("<!-- csrf_token -->"), 1)
				# The marker becomes `frappe.csrf_token = ...`, so `frappe`
				# has to exist first on these standalone pages.
				self.assertLess(
					html.index("window.frappe = window.frappe || {}"),
					html.index("<!-- csrf_token -->"),
				)
				self.assertIn("window.frappe && window.frappe.csrf_token", html)


def _run_lifetime_patch(stored):
	frappe = types.ModuleType("frappe")
	written = {}
	frappe.db = types.SimpleNamespace(
		get_single_value=lambda doctype, field: stored,
		set_single_value=lambda doctype, field, value: written.update({field: value}),
	)
	utils = types.ModuleType("frappe.utils")

	def cint(v):
		try:
			return int(float(v or 0))
		except (TypeError, ValueError):
			return 0

	utils.cint = cint
	frappe.utils = utils
	with mock.patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils}):
		spec = importlib.util.spec_from_file_location(
			"lengthen_password_link_lifetime",
			WWW.parent / "patches/lengthen_password_link_lifetime.py",
		)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		module.execute()
	return written.get("reset_password_link_expiry_duration")


class LinkLifetime(unittest.TestCase):
	def test_frappes_twenty_minute_default_becomes_a_day(self):
		self.assertEqual(_run_lifetime_patch(1200), 86400)
		self.assertEqual(_run_lifetime_patch("1200"), 86400)

	def test_a_lifetime_someone_chose_is_left_alone(self):
		self.assertIsNone(_run_lifetime_patch(3600))

	def test_links_that_never_expire_are_not_shortened(self):
		self.assertIsNone(_run_lifetime_patch(0))
		self.assertIsNone(_run_lifetime_patch(None))


if __name__ == "__main__":
	unittest.main()
