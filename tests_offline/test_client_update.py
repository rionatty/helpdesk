"""Weekly client update (helpdesk/api/client_update.py): the pure parts -
recipient parsing, sorting work into the email's sections, the "nothing to
report" rule, and HTML escaping - tested without a bench."""

import importlib.util
import sys
import types
import unittest
from datetime import date, timedelta
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/client_update.py"


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	for name in (
		"add_days", "cint", "formatdate", "get_datetime", "get_url",
		"getdate", "now_datetime", "validate_email_address",
	):
		setattr(utils, name, lambda *a, **k: None)
	utils.cint = lambda v: int(float(v or 0))
	frappe.utils = utils
	saved = {k: sys.modules.get(k) for k in ("frappe", "frappe.utils")}
	sys.modules.update({"frappe": frappe, "frappe.utils": utils})
	try:
		spec = importlib.util.spec_from_file_location("client_update_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


cu = _load()

TODAY = date(2026, 10, 5)
SINCE = TODAY - timedelta(days=7)
AHEAD = TODAY + timedelta(days=14)
D = lambda n: TODAY + timedelta(days=n)  # noqa: E731


class TestRecipients(unittest.TestCase):
	def test_splits_and_dedupes(self):
		self.assertEqual(
			cu.parse_recipients("a@x.com, b@y.com; A@X.COM\nc@z.com  d@w.com"),
			["a@x.com", "b@y.com", "c@z.com", "d@w.com"],
		)

	def test_empty(self):
		self.assertEqual(cu.parse_recipients(""), [])
		self.assertEqual(cu.parse_recipients(None), [])


class TestSections(unittest.TestCase):
	def setUp(self):
		self.milestones = [
			{"title": "Signed-off ask", "status": "In Progress", "signoff_status": "Requested"},
			{"title": "Done this week", "status": "Completed", "completed_on": D(-2)},
			{"title": "Done long ago", "status": "Completed", "completed_on": D(-30)},
			{"title": "Due soon", "status": "Upcoming", "due_date": D(5)},
			{"title": "Due far", "status": "Upcoming", "due_date": D(40)},
			{"title": "Already past", "status": "Missed", "due_date": D(-3)},
		]
		self.tasks = [
			{"subject": "Client, late", "status": "Pending", "responsibility": "Client", "end_date": D(-2)},
			{"subject": "Joint, soon", "status": "To Do", "responsibility": "Joint", "end_date": D(3)},
			{"subject": "Client, no date", "status": "To Do", "responsibility": "Client"},
			{"subject": "Client, done", "status": "Done", "responsibility": "Client", "completed_on": D(-1)},
			{"subject": "Ours, soon", "status": "In Progress", "responsibility": "Us", "end_date": D(4)},
			{"subject": "Ours, far", "status": "To Do", "responsibility": "Us", "end_date": D(60)},
			{"subject": "Ours, done old", "status": "Done", "responsibility": "Us", "completed_on": D(-20)},
			{"subject": "Review me", "status": "Done", "customer_review": "Requested", "completed_on": D(-30)},
		]
		self.s = cu.sections(self.milestones, self.tasks, TODAY, SINCE, AHEAD)

	def subjects(self, key, field="subject"):
		return [r[field] for r in self.s[key]]

	def test_waiting_is_client_and_joint_work_soonest_first(self):
		self.assertEqual(
			self.subjects("waiting"), ["Client, late", "Joint, soon", "Client, no date"]
		)

	def test_signoffs_and_reviews(self):
		self.assertEqual(self.subjects("signoffs", "title"), ["Signed-off ask"])
		self.assertEqual(self.subjects("reviews"), ["Review me"])

	def test_done_this_week_only(self):
		self.assertEqual(self.subjects("done_milestones", "title"), ["Done this week"])
		self.assertEqual(self.subjects("done_tasks"), ["Client, done"])

	def test_coming_up_within_the_window_and_not_repeating_waiting(self):
		self.assertEqual(self.subjects("upcoming_milestones", "title"), ["Due soon"])
		# "Joint, soon" is due in the window but already under "waiting".
		self.assertEqual(self.subjects("upcoming_tasks"), ["Ours, soon"])

	def test_quiet_week_has_no_news(self):
		empty = cu.sections([], [{"subject": "x", "status": "Done", "completed_on": D(-30)}], TODAY, SINCE, AHEAD)
		self.assertFalse(cu.has_news(empty))
		self.assertTrue(cu.has_news(self.s))


class TestRender(unittest.TestCase):
	LINKS = {"project": "https://h.example/p", "ticket": lambda n: f"https://h.example/t/{n}"}

	def render(self, s, tickets=(), progress=40):
		return cu.render("Project <X>", s, list(tickets), progress, TODAY, self.LINKS)

	def test_escapes_everything_customer_written(self):
		s = cu.sections([], [{"subject": "<script>alert(1)</script>", "status": "To Do", "responsibility": "Client"}], TODAY, SINCE, AHEAD)
		out = self.render(s, tickets=[{"name": "T1", "subject": "<img src=x onerror=1>", "status": "Open"}])
		self.assertNotIn("<script>", out)
		self.assertNotIn("<img", out)
		self.assertIn("&lt;script&gt;", out)
		self.assertIn("Project &lt;X&gt;", out)

	def test_marks_overdue_client_work(self):
		s = cu.sections([], [{"subject": "Late one", "status": "To Do", "responsibility": "Client", "end_date": D(-2)}], TODAY, SINCE, AHEAD)
		self.assertIn("overdue since", self.render(s))

	def test_only_sections_with_content_appear(self):
		s = cu.sections([{"title": "M", "status": "Completed", "completed_on": D(-1)}], [], TODAY, SINCE, AHEAD)
		out = self.render(s)
		self.assertIn("Done this week", out)
		self.assertNotIn("Waiting on you", out)
		self.assertNotIn("Your open tickets", out)

	def test_progress_is_clamped(self):
		s = cu.sections([{"title": "M", "status": "Completed", "completed_on": D(-1)}], [], TODAY, SINCE, AHEAD)
		self.assertIn("width:100%", self.render(s, progress=150))
		self.assertIn("width:0%", self.render(s, progress=-5))


if __name__ == "__main__":
	unittest.main()
