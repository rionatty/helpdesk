"""Job cards (helpdesk/api/job_card.py): the pure parts - what saving a
card's lines does to the time ledger, signature checks, times of day, and
the printout's escaping - tested without a bench."""

import importlib.util
import sys
import types
import unittest
from datetime import timedelta
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/api/job_card.py"


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
	for name in (
		"format_date", "format_datetime", "get_fullname", "get_url", "getdate",
		"now_datetime", "nowdate", "strip_html", "to_timedelta",
	):
		setattr(utils, name, lambda *a, **k: None)
	frappe.utils = utils
	werkzeug = types.ModuleType("werkzeug")
	wrappers = types.ModuleType("werkzeug.wrappers")
	wrappers.Response = object
	helpdesk = types.ModuleType("helpdesk")
	api = types.ModuleType("helpdesk.api")
	contracts = types.ModuleType("helpdesk.api.contracts")
	api.contracts = contracts
	hd_utils = types.ModuleType("helpdesk.utils")
	for name in ("get_customer", "is_agent", "is_agent_manager"):
		setattr(hd_utils, name, lambda *a, **k: None)
	stand_ins = {
		"frappe": frappe,
		"frappe.utils": utils,
		"werkzeug": werkzeug,
		"werkzeug.wrappers": wrappers,
		"helpdesk": helpdesk,
		"helpdesk.api": api,
		"helpdesk.api.contracts": contracts,
		"helpdesk.utils": hd_utils,
	}
	saved = {k: sys.modules.get(k) for k in stand_ins}
	sys.modules.update(stand_ins)
	try:
		spec = importlib.util.spec_from_file_location("job_card_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module


jc = _load()
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


class TestPlanLines(unittest.TestCase):
	def test_a_new_card_from_a_ticket(self):
		incoming = [
			{"time_log": "TL1", "from_card": 0},  # the ticket's logged time
			{"hours": 1},  # typed on the card
		]
		plan = jc.plan_lines([], incoming, log_time=True)
		self.assertEqual(plan["link"], ["TL1"])
		self.assertEqual(plan["create"], [1])
		self.assertEqual(plan["update"] + plan["delete"] + plan["unlink"], [])

	def test_typed_time_not_counted_when_asked(self):
		self.assertEqual(jc.plan_lines([], [{"hours": 2}], log_time=False)["create"], [])

	def test_editing_keeps_the_card_logs_in_step(self):
		old = [{"time_log": "TL1", "from_card": 0}, {"time_log": "TL2", "from_card": 1}]
		incoming = [{"time_log": "TL1", "from_card": 0}, {"time_log": "TL2", "from_card": 1}]
		plan = jc.plan_lines(old, incoming, log_time=True)
		self.assertEqual(plan["update"], ["TL2"])
		self.assertEqual(plan["link"], ["TL1"])

	def test_removed_lines(self):
		old = [{"time_log": "TL1", "from_card": 0}, {"time_log": "TL2", "from_card": 1}]
		plan = jc.plan_lines(old, [], log_time=True)
		# The ticket's time stays logged, off the card; the card's own goes.
		self.assertEqual(plan["unlink"], ["TL1"])
		self.assertEqual(plan["delete"], ["TL2"])

	def test_old_lines_without_a_log_are_ignored(self):
		plan = jc.plan_lines([{"time_log": None, "from_card": 0}], [], log_time=True)
		self.assertEqual(plan["unlink"] + plan["delete"], [])


class TestHelpers(unittest.TestCase):
	def test_total_hours(self):
		self.assertEqual(jc.total_hours([{"hours": 1.25}, {"hours": "0.5"}, {"hours": None}]), 1.75)

	def test_signature(self):
		self.assertTrue(jc.valid_signature(PNG))
		self.assertFalse(jc.valid_signature("data:image/svg+xml;base64,PHN2Zz4="))
		self.assertFalse(jc.valid_signature("javascript:alert(1)"))
		self.assertFalse(jc.valid_signature(PNG + "'><script>"))
		self.assertFalse(jc.valid_signature(None))
		self.assertFalse(jc.valid_signature("data:image/png;base64," + "A" * jc.MAX_SIGNATURE_CHARS))

	def test_clock(self):
		self.assertEqual(jc.clock(timedelta(hours=9, minutes=5)), "09:05")
		self.assertEqual(jc.clock("14:30:00"), "14:30")
		self.assertEqual(jc.clock("7:15"), "07:15")
		self.assertEqual(jc.clock(None), "")


class TestRender(unittest.TestCase):
	CTX = {"brand_name": "CyveTech", "logo_url": None, "footer": "Kampala\nwww.cyvetech.com", "generated_at": "6 Oct 2026"}

	def card(self, **kw):
		base = {
			"name": "JC-2026-00001",
			"status": "Open",
			"customer": "Acme <Ltd>",
			"contact_name": "Ann",
			"date_label": "6 Oct 2026",
			"service_type": "On-site",
			"technician_name": "Ferdinand",
			"work_requested": "Printer <b>down</b>\nsince 9am",
			"work_done": "Replaced toner",
			"work_status": "Resolved",
			"lines": [{"date_label": "6 Oct", "description": "<script>x</script>", "technician_name": "F", "hours": 1.5}],
			"items": [{"description": "Toner & drum", "quantity": 1}],
			"total_hours": 1.5,
		}
		base.update(kw)
		return base

	def test_everything_typed_is_escaped(self):
		out = jc.render_card(self.card(), self.CTX)
		self.assertIn("Acme &lt;Ltd&gt;", out)
		self.assertIn("Printer &lt;b&gt;down&lt;/b&gt;<br>since 9am", out)
		self.assertIn("&lt;script&gt;x&lt;/script&gt;", out)
		self.assertIn("Toner &amp; drum", out)
		self.assertNotIn("<script>x", out)
		self.assertIn("Kampala<br>www.cyvetech.com", out)

	def test_lines_and_total(self):
		out = jc.render_card(self.card(), self.CTX)
		self.assertIn("Time spent", out)
		self.assertIn(">1.5<", out)

	def test_signature_only_when_it_is_a_png(self):
		signed = jc.render_card(self.card(status="Signed", signed_by="Ann", customer_signature=PNG, satisfied=1), self.CTX)
		self.assertIn(f"src='{PNG}'", signed)
		self.assertIn("Work accepted as satisfactory", signed)
		forged = jc.render_card(self.card(status="Signed", signed_by="Ann", customer_signature="x' onerror='alert(1)"), self.CTX)
		self.assertNotIn("onerror", forged)

	def test_autoprint_only_when_asked(self):
		self.assertNotIn("window.print()},", jc.render_card(self.card(), self.CTX))
		self.assertIn("window.print()},", jc.render_card(self.card(), {**self.CTX, "autoprint": 1}))

	def test_logo_address_is_escaped(self):
		out = jc.render_card(self.card(), {**self.CTX, "logo_url": 'https://x/logo.png" onload="alert(1)'})
		self.assertNotIn('" onload="', out)


if __name__ == "__main__":
	unittest.main()
