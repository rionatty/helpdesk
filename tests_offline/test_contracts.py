"""Support contracts (helpdesk/api/contracts.py): the pure parts - which
period a day falls in, usage and alert levels, contract states, overlapping
terms, taking corrected subtask hours back, and what the client and the
managers are shown - tested without a bench."""

import importlib.util
import sys
import types
import unittest
from datetime import date
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/contracts.py"


def _flt(v):
	try:
		return float(v or 0)
	except (TypeError, ValueError):
		return 0.0


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda v: int(float(v or 0))
	utils.flt = _flt
	utils.get_url = lambda: "https://support.example.com"
	utils.getdate = lambda v=None: v
	utils.nowdate = lambda: date(2026, 10, 5)
	frappe.utils = utils
	helpdesk = types.ModuleType("helpdesk")
	hd_utils = types.ModuleType("helpdesk.utils")
	hd_utils.get_customer = lambda user: []
	hd_utils.is_agent = lambda user=None: True
	hd_utils.is_agent_manager = lambda user=None: False
	helpdesk.utils = hd_utils
	stand_ins = {
		"frappe": frappe,
		"frappe.utils": utils,
		"helpdesk": helpdesk,
		"helpdesk.utils": hd_utils,
	}
	saved = {k: sys.modules.get(k) for k in stand_ins}
	sys.modules.update(stand_ins)
	try:
		spec = importlib.util.spec_from_file_location("contracts_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


c = _load()
D = date


class TestPeriodWindow(unittest.TestCase):
	def test_monthly_follows_the_calendar(self):
		self.assertEqual(
			c.period_window("Monthly", D(2026, 1, 15), None, D(2026, 10, 5)),
			(D(2026, 10, 1), D(2026, 10, 31), "October 2026"),
		)

	def test_monthly_leap_february(self):
		f, t, _ = c.period_window("Monthly", D(2026, 1, 1), None, D(2028, 2, 10))
		self.assertEqual((f, t), (D(2028, 2, 1), D(2028, 2, 29)))

	def test_clipped_to_the_contract(self):
		f, t, _ = c.period_window("Monthly", D(2026, 10, 3), D(2026, 10, 20), D(2026, 10, 5))
		self.assertEqual((f, t), (D(2026, 10, 3), D(2026, 10, 20)))

	def test_quarterly(self):
		self.assertEqual(
			c.period_window("Quarterly", D(2026, 1, 1), None, D(2026, 11, 15)),
			(D(2026, 10, 1), D(2026, 12, 31), "Q4 2026"),
		)
		f, t, label = c.period_window("Quarterly", D(2025, 6, 1), None, D(2026, 2, 1))
		self.assertEqual((f, t, label), (D(2026, 1, 1), D(2026, 3, 31), "Q1 2026"))

	def test_yearly_runs_from_the_start_anniversary(self):
		start = D(2025, 3, 15)
		self.assertEqual(
			c.period_window("Yearly", start, None, D(2026, 10, 5))[:2],
			(D(2026, 3, 15), D(2027, 3, 14)),
		)
		self.assertEqual(
			c.period_window("Yearly", start, None, D(2026, 3, 14))[:2],
			(D(2025, 3, 15), D(2026, 3, 14)),
		)
		self.assertEqual(
			c.period_window("Yearly", start, None, D(2026, 3, 15))[:2],
			(D(2026, 3, 15), D(2027, 3, 14)),
		)

	def test_yearly_from_29_february_leaves_no_gap(self):
		start = D(2024, 2, 29)
		day = D(2024, 2, 29)
		previous = None
		while day < D(2032, 3, 1):
			window = c.period_window("Yearly", start, None, day)[:2]
			f, t = window
			self.assertTrue(f <= day <= t, f"{day} is outside its window {f}..{t}")
			if previous and window != previous:
				self.assertEqual((f - previous[1]).days, 1, f"gap or overlap before {f}")
			previous = window
			day = D.fromordinal(day.toordinal() + 1)

	def test_whole_contract(self):
		self.assertEqual(
			c.period_window("Whole contract", D(2026, 1, 1), None, D(2026, 10, 5)),
			(D(2026, 1, 1), D(2026, 10, 5), "Whole contract"),
		)
		self.assertEqual(
			c.period_window("Whole contract", D(2026, 1, 1), D(2026, 12, 31), D(2026, 10, 5))[:2],
			(D(2026, 1, 1), D(2026, 12, 31)),
		)


class TestUsage(unittest.TestCase):
	def test_usage(self):
		self.assertEqual(
			c.usage_of(10, 6.5), {"included": 10, "used": 6.5, "remaining": 3.5, "pct": 65}
		)

	def test_over_the_limit(self):
		u = c.usage_of(10, 12)
		self.assertEqual((u["remaining"], u["pct"]), (-2, 120))

	def test_no_included_hours(self):
		self.assertEqual(c.usage_of(0, 3)["pct"], 0)


class TestThresholds(unittest.TestCase):
	def test_crossing_the_alert_level(self):
		self.assertEqual(c.thresholds_crossed(7, 8.5, 10, 80), [80])

	def test_crossing_both_at_once(self):
		self.assertEqual(c.thresholds_crossed(7, 11, 10, 80), [80, 100])

	def test_already_past_it(self):
		self.assertEqual(c.thresholds_crossed(8.5, 9, 10, 80), [])

	def test_exactly_reaching_100(self):
		self.assertEqual(c.thresholds_crossed(9, 10, 10, 80), [100])

	def test_alert_level_of_100_alerts_once(self):
		self.assertEqual(c.thresholds_crossed(9, 10, 10, 100), [100])

	def test_float_error_does_not_hide_a_crossing(self):
		self.assertEqual(c.thresholds_crossed(0.1 + 0.6, 0.1 + 0.7, 1, 80), [80])

	def test_going_down_never_alerts(self):
		self.assertEqual(c.thresholds_crossed(11, 7, 10, 80), [])

	def test_no_included_hours(self):
		self.assertEqual(c.thresholds_crossed(0, 5, 0, 80), [])

	def test_default_level(self):
		self.assertEqual(c.thresholds_crossed(7, 8, 10, None), [80])


class TestState(unittest.TestCase):
	def test_states(self):
		start, end = D(2026, 1, 1), D(2026, 12, 31)
		self.assertEqual(c.contract_state("Cancelled", start, end, D(2026, 6, 1)), "Cancelled")
		self.assertEqual(c.contract_state("Active", start, end, D(2025, 12, 31)), "Not started")
		self.assertEqual(c.contract_state("Active", start, end, D(2027, 1, 1)), "Ended")
		self.assertEqual(c.contract_state("Active", start, end, D(2026, 12, 31)), "In force")
		self.assertEqual(c.contract_state("Active", start, None, D(2030, 1, 1)), "In force")


class TestOverlaps(unittest.TestCase):
	def test_open_ended_overlaps_everything_after(self):
		self.assertTrue(c.overlaps(D(2026, 1, 1), None, D(2027, 1, 1), D(2027, 12, 31)))

	def test_back_to_back_terms_do_not_overlap(self):
		self.assertFalse(
			c.overlaps(D(2026, 1, 1), D(2026, 6, 30), D(2026, 7, 1), D(2026, 12, 31))
		)

	def test_sharing_one_day_overlaps(self):
		self.assertTrue(
			c.overlaps(D(2026, 1, 1), D(2026, 6, 30), D(2026, 6, 30), D(2026, 12, 31))
		)


class TestTakeBack(unittest.TestCase):
	def test_from_the_newest_entry(self):
		self.assertEqual(c.take_back([2, 1.5], 0.5), [1.5, 1.5])

	def test_spills_into_older_entries(self):
		self.assertEqual(c.take_back([0.5, 2], 1), [0, 1.5])

	def test_never_below_zero(self):
		self.assertEqual(c.take_back([1], 3), [0])

	def test_nothing_to_take(self):
		self.assertEqual(c.take_back([2], 0), [2])


class TestWording(unittest.TestCase):
	def test_client_line(self):
		self.assertEqual(c.client_line("Call with finance", "Fix print", "12"), "Call with finance")
		self.assertEqual(c.client_line(None, "Fix print", "12"), "Fix print")
		self.assertEqual(c.client_line(None, None, "12"), "Ticket #12")
		self.assertEqual(c.client_line(None, None, None), "Support")

	def test_alert_subject(self):
		self.assertEqual(
			c.alert_subject("Acme", {"pct": 85}), "Acme has used 85% of its support hours"
		)
		self.assertEqual(
			c.alert_subject("Acme", {"pct": 110}), "Acme has used all its support hours (110%)"
		)

	def test_alert_body_escapes_names(self):
		contract = types.SimpleNamespace(
			customer="<b>Acme & Co</b>", contract_name="<script>x</script>", name="C1"
		)
		usage = {
			"used": 8.5, "included": 10, "pct": 85, "remaining": 1.5, "period_label": "October 2026",
		}
		body = c.alert_body(contract, usage, "https://support.example.com")
		self.assertIn("&lt;b&gt;Acme &amp; Co&lt;/b&gt;", body)
		self.assertNotIn("<script>", body)
		self.assertIn("1.5 h left", body)
		self.assertIn('href="https://support.example.com/helpdesk/contracts"', body)

	def test_alert_body_over(self):
		contract = types.SimpleNamespace(customer="Acme", contract_name="Gold", name="C1")
		usage = {"used": 12, "included": 10, "pct": 120, "remaining": -2, "period_label": "Q4 2026"}
		self.assertIn("2 h over", c.alert_body(contract, usage, "https://x"))


if __name__ == "__main__":
	unittest.main()
