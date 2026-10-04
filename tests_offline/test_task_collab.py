"""Task @mentions and watchers (helpdesk/api/task_collab.py): who gets told
about what, and that the emails are escaped - tested without a bench."""

import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/task_collab.py"


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda v: int(float(v or 0))
	utils.get_url = lambda: "https://h.example"
	utils.strip_html = lambda s: re.sub(r"<[^>]+>", "", s)
	frappe.utils = utils
	helpdesk = types.ModuleType("helpdesk")
	helpdesk_utils = types.ModuleType("helpdesk.utils")
	helpdesk_utils.is_agent = lambda: True
	names = ("frappe", "frappe.utils", "helpdesk", "helpdesk.utils")
	saved = {k: sys.modules.get(k) for k in names}
	sys.modules.update(
		{"frappe": frappe, "frappe.utils": utils, "helpdesk": helpdesk, "helpdesk.utils": helpdesk_utils}
	)
	try:
		spec = importlib.util.spec_from_file_location("task_collab_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


tc = _load()


class TestAudiences(unittest.TestCase):
	def test_nobody_hears_about_their_own_action(self):
		mentioned, others = tc.audiences({"me", "ann", "bob"}, {"me"}, "me")
		self.assertEqual(mentioned, set())
		self.assertEqual(others, {"ann", "bob"})

	def test_a_mentioned_watcher_gets_the_mention_not_both(self):
		mentioned, others = tc.audiences({"ann", "bob"}, {"ann", "cy"}, "me")
		self.assertEqual(mentioned, {"ann", "cy"})
		self.assertEqual(others, {"bob"})

	def test_skip_drops_people_another_email_covers(self):
		_, others = tc.audiences({"ann", "bob", "rev"}, (), "me", skip={"rev"})
		self.assertEqual(others, {"ann", "bob"})

	def test_blanks_ignored(self):
		mentioned, others = tc.audiences({None, "", "ann"}, {None, ""}, "me")
		self.assertEqual((mentioned, others), (set(), {"ann"}))


class TestEmailBody(unittest.TestCase):
	def test_customer_text_is_escaped(self):
		body = tc.email_body("<b>X</b> commented", "<script>alert(1)</script> hi", "https://h.example/p", "why")
		self.assertNotIn("<script>", body)
		self.assertIn("alert(1)", body)  # tags stripped, text kept
		self.assertIn("<b>X</b>", body)  # the headline is ours and keeps its markup

	def test_long_comments_are_cut(self):
		body = tc.email_body("h", "x" * 2000, "https://h.example", "r")
		self.assertIn("…", body)
		self.assertLess(len(body), 2000)

	def test_no_quote_block_without_text(self):
		self.assertNotIn("blockquote", tc.email_body("h", "", "https://h.example", "r"))


if __name__ == "__main__":
	unittest.main()
