"""Assignment and expected-resolution notices (helpdesk/api/assignment.py):
the pure parts - rounding the expected resolution, and what the customer is
told, escaped - tested without a bench."""

import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/assignment.py"


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda v: int(float(v or 0))
	utils.flt = lambda v: float(v or 0)
	for name in ("format_datetime", "get_datetime", "get_fullname", "now_datetime"):
		setattr(utils, name, lambda *a, **k: None)
	frappe.utils = utils
	helpdesk = types.ModuleType("helpdesk")
	hd_utils = types.ModuleType("helpdesk.utils")
	hd_utils.is_agent = lambda user=None: True
	hd_utils.is_agent_manager = lambda user=None: False
	stand_ins = {"frappe": frappe, "frappe.utils": utils, "helpdesk": helpdesk, "helpdesk.utils": hd_utils}
	saved = {k: sys.modules.get(k) for k in stand_ins}
	sys.modules.update(stand_ins)
	try:
		spec = importlib.util.spec_from_file_location("assignment_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


a = _load()
URL = "https://support.example.com/helpdesk/my-tickets/42"


class TestEta(unittest.TestCase):
	def test_rounds_up_to_the_quarter_hour(self):
		self.assertEqual(a.round_up(datetime(2026, 10, 20, 10, 7, 33)), datetime(2026, 10, 20, 10, 15))
		self.assertEqual(a.round_up(datetime(2026, 10, 20, 10, 45, 0)), datetime(2026, 10, 20, 10, 45))
		self.assertEqual(a.round_up(datetime(2026, 10, 20, 23, 50)), datetime(2026, 10, 21, 0, 0))

	def test_hours_from_now(self):
		now = datetime(2026, 10, 20, 9, 52)
		self.assertEqual(a.eta_from_hours(now, 4), datetime(2026, 10, 20, 14, 0))
		self.assertEqual(a.eta_from_hours(now, 48), datetime(2026, 10, 22, 10, 0))

	def test_first_name(self):
		self.assertEqual(a.first_name("Grace Achieng"), "Grace")
		self.assertEqual(a.first_name(None), "")


class TestMessages(unittest.TestCase):
	def test_assignment(self):
		html, text = a.assignment_message("Alex Kim", "42", "Printer down", None, URL, "Grace")
		self.assertIn("Hello Grace,", html)
		self.assertIn("Alex Kim is now handling your ticket #42: Printer down.", html)
		self.assertIn(f'<a href="{URL}">', html)
		self.assertNotIn("expect", html)
		self.assertEqual(text, "Alex Kim is now handling your ticket #42: Printer down.")

	def test_assignment_with_expected_resolution(self):
		html, text = a.assignment_message("Alex", "42", "Printer down", "Tue 21 Oct, 15:00", URL)
		self.assertIn("Hello,", html)
		self.assertIn("They expect to resolve it by Tue 21 Oct, 15:00.", html)
		self.assertTrue(text.endswith("They expect to resolve it by Tue 21 Oct, 15:00."))

	def test_customer_text_is_escaped(self):
		html, _text = a.assignment_message("Alex", "42", "<script>x</script> & co", None, URL, "<b>G</b>")
		self.assertIn("&lt;script&gt;x&lt;/script&gt; &amp; co", html)
		self.assertIn("&lt;b&gt;G&lt;/b&gt;", html)
		self.assertNotIn("<script>", html)

	def test_new_and_moved_expected_resolution(self):
		html, text = a.eta_message("Alex", "42", "Printer down", "Tue 21 Oct, 15:00", None, URL)
		self.assertEqual(text, "Alex expects to resolve your ticket #42: Printer down by Tue 21 Oct, 15:00.")
		html, text = a.eta_message("Alex", "42", "Printer down", "Wed 22 Oct, 10:00", "Tue 21 Oct, 15:00", URL)
		self.assertIn("now expects", text)
		self.assertIn("(it was Tue 21 Oct, 15:00)", text)


if __name__ == "__main__":
	unittest.main()
