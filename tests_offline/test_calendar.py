"""The calendar's clash rules (helpdesk/api/calendar.py), tested without a
bench: when two of a person's sessions collide, and when they don't.

- Only sessions clash (Onsite / Online). Ordinary tasks run alongside other
  work by design.
- A session with both times set occupies exactly that slot; without times it
  takes its whole day(s).
- Back-to-back sessions (10:00-12:00, then 12:00-14:00) are fine.
- Done and Postponed sessions occupy nothing.
"""

import importlib.util
import sys
import types
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest import mock

CALENDAR = Path(__file__).resolve().parents[1] / "helpdesk/api/calendar.py"


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	utils = types.ModuleType("frappe.utils")
	utils.getdate = lambda v: date.fromisoformat(str(v)[:10])
	frappe.utils = utils
	hd_utils = types.ModuleType("helpdesk.utils")
	hd_utils.is_agent = lambda user=None: True
	hd_utils.is_agent_manager = lambda user=None: True
	stand_ins = {
		"frappe": frappe,
		"frappe.utils": utils,
		"helpdesk.utils": hd_utils,
	}
	with mock.patch.dict(sys.modules, stand_ins):
		spec = importlib.util.spec_from_file_location("calendar_under_test", CALENDAR)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	return module


cal = _load()


def task(name, who="ana@cyvetech.com", day="2026-11-03", start=None, end=None,
		kind="Onsite", status="To Do", end_day=None):
	return {
		"name": name,
		"assigned_to": who,
		"session_type": kind,
		"status": status,
		"start_date": day,
		"end_date": end_day or day,
		"start_time": start,
		"end_time": end,
	}


class Times(unittest.TestCase):
	def test_a_database_time_arrives_as_a_timedelta(self):
		self.assertEqual(cal.as_time(timedelta(hours=9, minutes=30)), time(9, 30))

	def test_a_form_time_arrives_as_text(self):
		self.assertEqual(cal.as_time("9:05"), time(9, 5))
		self.assertEqual(cal.as_time("14:00:00"), time(14, 0))

	def test_no_time_is_none(self):
		self.assertIsNone(cal.as_time(None))
		self.assertIsNone(cal.as_time(""))

	def test_times_go_out_as_hours_and_minutes(self):
		self.assertEqual(cal.hhmm(timedelta(hours=7)), "07:00")
		self.assertIsNone(cal.hhmm(None))


class Window(unittest.TestCase):
	def test_a_timed_session_occupies_its_slot(self):
		start, end, timed = cal.session_window(task("A", start="10:00", end="12:00"))
		self.assertEqual((start, end, timed), (
			datetime(2026, 11, 3, 10), datetime(2026, 11, 3, 12), True))

	def test_a_session_without_times_takes_the_whole_day(self):
		start, end, timed = cal.session_window(task("A"))
		self.assertEqual((start, end, timed), (
			datetime(2026, 11, 3), datetime(2026, 11, 4), False))

	def test_a_multi_day_session_takes_every_day(self):
		start, end, _t = cal.session_window(task("A", end_day="2026-11-05"))
		self.assertEqual((start, end), (datetime(2026, 11, 3), datetime(2026, 11, 6)))

	def test_only_a_due_date_means_that_one_day(self):
		t = task("A")
		t["start_date"] = None
		start, end, _t = cal.session_window(t)
		self.assertEqual((start, end), (datetime(2026, 11, 3), datetime(2026, 11, 4)))

	def test_dates_entered_backwards_are_tolerated(self):
		t = task("A", day="2026-11-05", end_day="2026-11-03")
		start, end, _t = cal.session_window(t)
		self.assertEqual((start, end), (datetime(2026, 11, 5), datetime(2026, 11, 6)))

	def test_only_one_time_set_counts_as_the_whole_day(self):
		self.assertFalse(cal.session_window(task("A", start="10:00"))[2])

	def test_no_date_at_all_has_no_window(self):
		t = task("A")
		t["start_date"] = t["end_date"] = None
		self.assertIsNone(cal.session_window(t))


class Clash(unittest.TestCase):
	def test_overlapping_sessions_for_one_person_clash(self):
		a = task("A", start="10:00", end="12:00")
		b = task("B", start="11:00", end="13:00", kind="Online")
		self.assertTrue(cal.sessions_clash(a, b))

	def test_back_to_back_sessions_do_not_clash(self):
		a = task("A", start="10:00", end="12:00")
		b = task("B", start="12:00", end="14:00")
		self.assertFalse(cal.sessions_clash(a, b))

	def test_a_whole_day_onsite_clashes_with_any_session_that_day(self):
		a = task("A")  # onsite, all day
		b = task("B", start="16:00", end="17:00", kind="Online")
		self.assertTrue(cal.sessions_clash(a, b))

	def test_a_multi_day_onsite_clashes_with_a_session_inside_it(self):
		a = task("A", day="2026-11-02", end_day="2026-11-04")
		b = task("B", day="2026-11-03", start="14:00", end="15:00", kind="Online")
		self.assertTrue(cal.sessions_clash(a, b))

	def test_different_people_never_clash(self):
		a = task("A", start="10:00", end="12:00")
		b = task("B", who="ben@cyvetech.com", start="10:00", end="12:00")
		self.assertFalse(cal.sessions_clash(a, b))

	def test_an_ordinary_task_never_clashes(self):
		a = task("A", start="10:00", end="12:00")
		b = task("B", kind=None)
		self.assertFalse(cal.sessions_clash(a, b))

	def test_done_and_postponed_sessions_occupy_nothing(self):
		a = task("A", start="10:00", end="12:00")
		for status in ("Done", "Postponed"):
			b = task("B", start="10:00", end="12:00", status=status)
			self.assertFalse(cal.sessions_clash(a, b), status)

	def test_a_session_does_not_clash_with_itself(self):
		a = task("A", start="10:00", end="12:00")
		self.assertFalse(cal.sessions_clash(a, dict(a)))

	def test_an_unassigned_session_clashes_with_nobody(self):
		a = task("A", who=None, start="10:00", end="12:00")
		b = task("B", who=None, start="10:00", end="12:00")
		self.assertFalse(cal.sessions_clash(a, b))


class FindAll(unittest.TestCase):
	def test_only_the_colliding_sessions_are_flagged_both_ways(self):
		rows = [
			task("A1", start="09:00", end="11:00"),
			task("A2", start="10:00", end="12:00", kind="Online"),
			task("A3", start="13:00", end="14:00"),
			task("B1", who="ben@cyvetech.com", start="09:00", end="12:00"),
			task("T1", kind=None),
		]
		self.assertEqual(cal.find_clashes(rows), {"A1": ["A2"], "A2": ["A1"]})

	def test_one_long_session_can_clash_with_several(self):
		rows = [
			task("DAY"),  # onsite, all day
			task("M", start="09:00", end="10:00", kind="Online"),
			task("N", start="15:00", end="16:00", kind="Online"),
		]
		self.assertEqual(
			cal.find_clashes(rows), {"DAY": ["M", "N"], "M": ["DAY"], "N": ["DAY"]}
		)

	def test_a_session_on_another_day_is_left_alone(self):
		rows = [
			task("A", start="10:00", end="12:00"),
			task("B", day="2026-11-04", start="10:00", end="12:00"),
		]
		self.assertEqual(cal.find_clashes(rows), {})


if __name__ == "__main__":
	unittest.main()
