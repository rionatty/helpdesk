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

	def test_after_a_reset_only_a_path_on_this_site_is_followed(self):
		self.assertIn(r"/^\/(?!\/)/.test(res.data.message)", self.html)


if __name__ == "__main__":
	unittest.main()
