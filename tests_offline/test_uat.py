"""UAT scripts (helpdesk/api/uat.py): the pure parts - a script's status
from its steps, progress counts, keeping test results through an edit, and
the defect task's wording - tested without a bench."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/uat.py"


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda v: int(float(v or 0))
	for name in ("format_datetime", "get_url", "now_datetime", "validate_email_address"):
		setattr(utils, name, lambda *a, **k: None)
	frappe.utils = utils

	helpdesk = types.ModuleType("helpdesk")
	api = types.ModuleType("helpdesk.api")
	project = types.ModuleType("helpdesk.api.project")
	project._assert_agent_project = lambda *a, **k: None
	project._assert_project_access = lambda *a, **k: None
	integrations = types.ModuleType("helpdesk.integrations")
	pumble = types.ModuleType("helpdesk.integrations.pumble")
	integrations.pumble = pumble
	hd_utils = types.ModuleType("helpdesk.utils")
	hd_utils.is_agent = lambda user=None: True
	stand_ins = {
		"frappe": frappe,
		"frappe.utils": utils,
		"helpdesk": helpdesk,
		"helpdesk.api": api,
		"helpdesk.api.project": project,
		"helpdesk.integrations": integrations,
		"helpdesk.integrations.pumble": pumble,
		"helpdesk.utils": hd_utils,
	}
	saved = {k: sys.modules.get(k) for k in stand_ins}
	sys.modules.update(stand_ins)
	try:
		spec = importlib.util.spec_from_file_location("uat_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


uat = _load()


class TestScriptStatus(unittest.TestCase):
	def test_nothing_run(self):
		self.assertEqual(uat.script_status([]), "Not started")
		self.assertEqual(uat.script_status(["Not run", None]), "Not started")

	def test_all_passed(self):
		self.assertEqual(uat.script_status(["Passed", "Passed"]), "Passed")

	def test_one_failure_fails_the_script_even_mid_run(self):
		self.assertEqual(uat.script_status(["Passed", "Failed", "Not run"]), "Failed")

	def test_failure_outranks_a_blocker(self):
		self.assertEqual(uat.script_status(["Blocked", "Failed"]), "Failed")

	def test_blocked(self):
		self.assertEqual(uat.script_status(["Passed", "Blocked"]), "Blocked")

	def test_in_progress(self):
		self.assertEqual(uat.script_status(["Passed", "Not run"]), "In progress")


class TestStepCounts(unittest.TestCase):
	def test_counts(self):
		counts = uat.step_counts(
			[("Passed", False), ("Failed", True), ("Blocked", True), ("Not run", True), ("Not run", False)]
		)
		self.assertEqual(
			counts,
			{"total": 5, "passed": 1, "failed": 1, "blocked": 1, "not_run": 2, "retest": 1},
		)

	def test_empty(self):
		self.assertEqual(uat.step_counts([])["total"], 0)


class TestMergeSteps(unittest.TestCase):
	EXISTING = [
		{"name": "s1", "action": "Open the sales order", "expected": None, "outcome": "Passed",
		 "note": None, "tested_by": "c@client.com", "tested_on": "2026-10-01", "defect_task": None},
		{"name": "s2", "action": "Post the invoice", "expected": "Posted", "outcome": "Failed",
		 "note": "Error 500", "tested_by": "c@client.com", "tested_on": "2026-10-01", "defect_task": "T-9"},
	]

	def test_kept_steps_keep_their_results_in_the_new_order(self):
		out = uat.merge_steps(
			self.EXISTING,
			[
				{"name": "s2", "action": " Post the invoice ", "expected": "Posted, with VAT"},
				{"name": "s1", "action": "Open the sales order", "expected": ""},
			],
		)
		self.assertEqual([r["name"] for r in out], ["s2", "s1"])
		self.assertEqual(out[0]["outcome"], "Failed")
		self.assertEqual(out[0]["defect_task"], "T-9")
		self.assertEqual(out[0]["action"], "Post the invoice")
		self.assertEqual(out[0]["expected"], "Posted, with VAT")
		self.assertIsNone(out[1]["expected"])

	def test_new_steps_start_not_run_and_blank_ones_are_dropped(self):
		out = uat.merge_steps(
			self.EXISTING,
			[{"action": "Print it", "expected": "A PDF"}, {"action": "   ", "expected": "x"}],
		)
		self.assertEqual(out, [{"action": "Print it", "expected": "A PDF", "outcome": "Not run"}])

	def test_a_name_from_elsewhere_is_a_new_step(self):
		out = uat.merge_steps(self.EXISTING, [{"name": "other", "action": "New"}])
		self.assertEqual(out[0]["outcome"], "Not run")
		self.assertNotIn("name", out[0])

	def test_a_step_listed_twice_keeps_its_result_once(self):
		out = uat.merge_steps(
			self.EXISTING,
			[{"name": "s2", "action": "Post"}, {"name": "s2", "action": "Post again"}],
		)
		self.assertEqual(out[0]["outcome"], "Failed")
		self.assertEqual(out[1]["outcome"], "Not run")


class TestDefectWording(unittest.TestCase):
	def test_subject(self):
		self.assertEqual(
			uat.defect_subject("Failed", "Sales invoice", 3), "UAT failure: Sales invoice, step 3"
		)
		self.assertEqual(
			uat.defect_subject("Blocked", "Sales invoice", 1), "UAT blocker: Sales invoice, step 1"
		)

	def test_subject_fits_the_column(self):
		self.assertLessEqual(len(uat.defect_subject("Failed", "x" * 600, 1)), 500)

	def test_description(self):
		self.assertEqual(
			uat.defect_description(2, "Post the invoice", None, "Failed on 5 Oct by Ann: Error 500"),
			"Step 2: Post the invoice\nExpected: -\nFailed on 5 Oct by Ann: Error 500",
		)


if __name__ == "__main__":
	unittest.main()
