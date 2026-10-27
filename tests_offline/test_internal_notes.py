"""Internal notes on projects and tasks (helpdesk/api/notes.py), tested
without a bench. What must hold:

- Only agents who can work on the record read or write notes. A task's own
  access check also admits its customer, so the agent check has to come
  first - a customer must never get through to a task's notes.
- The author or a manager edits and deletes a note; anyone who can see it
  may pin it.
- Deleting a project or task takes its notes along, and does nothing when
  the table isn't there yet.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

NOTES = Path(__file__).resolve().parents[1] / "helpdesk/api/notes.py"
# Stand-ins for the modules notes.py imports, installed per test so they
# never leak into another test module.
STAND_INS: dict = {}

STATE = {
	"user": "agent@cyvetech.com",
	"agents": {"agent@cyvetech.com", "other@cyvetech.com", "boss@cyvetech.com"},
	"managers": {"boss@cyvetech.com"},
	"on_project": {"agent@cyvetech.com", "boss@cyvetech.com"},
	"table": True,
	"deleted": [],
	"docs": {},
	"saved": [],
}


class PermissionError_(Exception):
	pass


class Throw(Exception):
	pass


def _load():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	frappe.PermissionError = PermissionError_
	frappe.DoesNotExistError = type("DoesNotExistError", (Exception,), {})

	def throw(message, exc=None):
		raise (exc or Throw)(message)

	frappe.throw = throw
	class Session:
		@property
		def user(self):
			return STATE["user"]

	frappe.session = Session()
	frappe.db = types.SimpleNamespace(
		table_exists=lambda name: STATE["table"],
		delete=lambda doctype, filters: STATE["deleted"].append((doctype, filters)),
	)
	frappe.get_doc = lambda *a: STATE["docs"][a[1]] if len(a) == 2 else None
	frappe.delete_doc = lambda doctype, name, **k: STATE["deleted"].append((doctype, name))

	utils = types.ModuleType("frappe.utils")
	utils.get_fullname = lambda user: user
	utils.now_datetime = lambda: "NOW"
	utils.cint = lambda v: int(float(v or 0))
	frappe.utils = utils

	hd_utils = types.ModuleType("helpdesk.utils")
	hd_utils.is_agent = lambda user=None: (user or STATE["user"]) in STATE["agents"]
	hd_utils.is_agent_manager = lambda user=None: (user or STATE["user"]) in STATE["managers"]

	project_api = types.ModuleType("helpdesk.api.project")

	def assert_agent_project(project):
		if STATE["user"] not in STATE["on_project"]:
			raise PermissionError_("not on this project")

	project_api._assert_agent_project = assert_agent_project

	addon_api = types.ModuleType("helpdesk.api.addon")
	# Like the real one: it also lets the task's customer through.
	addon_api._assert_task_access = lambda task: None

	stand_ins = {
		"frappe": frappe,
		"frappe.utils": utils,
		"helpdesk": types.ModuleType("helpdesk"),
		"helpdesk.utils": hd_utils,
		"helpdesk.api": types.ModuleType("helpdesk.api"),
		"helpdesk.api.project": project_api,
		"helpdesk.api.addon": addon_api,
	}
	STAND_INS.update(stand_ins)
	with mock.patch.dict(sys.modules, STAND_INS):
		spec = importlib.util.spec_from_file_location("notes_under_test", NOTES)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	return module


notes = _load()


class Stubbed(unittest.TestCase):
	def setUp(self):
		patcher = mock.patch.dict(sys.modules, STAND_INS)
		patcher.start()
		self.addCleanup(patcher.stop)
		STATE["deleted"].clear()
		STATE["saved"].clear()
		STATE["table"] = True


class FakeNote:
	def __init__(self, name, owner, doctype="HD Project", ref="PROJ-1"):
		self.name = name
		self.owner = owner
		self.reference_doctype = doctype
		self.reference_name = ref
		self.content = "old"
		self.pinned = 0
		self.edited_on = None

	def save(self, **k):
		STATE["saved"].append(self.name)


def as_user(user):
	STATE["user"] = user


def note(owner="agent@cyvetech.com", **kw):
	n = FakeNote("N1", owner, **kw)
	STATE["docs"]["N1"] = n
	return n


class Access(Stubbed):
	def setUp(self):
		super().setUp()

	def test_a_project_member_reads_the_projects_notes(self):
		as_user("agent@cyvetech.com")
		notes._assert_note_access("HD Project", "PROJ-1")

	def test_an_agent_not_on_the_project_is_refused(self):
		as_user("other@cyvetech.com")
		with self.assertRaises(PermissionError_):
			notes._assert_note_access("HD Project", "PROJ-1")

	def test_a_customer_never_reaches_a_tasks_notes(self):
		# The task check alone would let them in; the agent check stops them.
		as_user("buyer@acme.com")
		with self.assertRaises(PermissionError_):
			notes._assert_note_access("HD Addon Task", "TASK-1")

	def test_notes_are_not_kept_on_other_doctypes(self):
		as_user("agent@cyvetech.com")
		with self.assertRaises(Throw):
			notes._assert_note_access("HD Ticket", "0001")


class Changing(Stubbed):
	def setUp(self):
		super().setUp()

	def test_the_author_can_change_their_note(self):
		self.assertTrue(notes.can_change("agent@cyvetech.com", "agent@cyvetech.com"))

	def test_a_manager_can_change_anyones_note(self):
		self.assertTrue(notes.can_change("agent@cyvetech.com", "boss@cyvetech.com"))

	def test_another_agent_cannot(self):
		self.assertFalse(notes.can_change("agent@cyvetech.com", "other@cyvetech.com"))

	def test_editing_someone_elses_note_is_refused(self):
		STATE["on_project"].add("other@cyvetech.com")
		try:
			note(owner="agent@cyvetech.com")
			as_user("other@cyvetech.com")
			with self.assertRaises(PermissionError_):
				notes.update_note("N1", content="mine now")
		finally:
			STATE["on_project"].discard("other@cyvetech.com")

	def test_anyone_who_can_see_a_note_can_pin_it(self):
		STATE["on_project"].add("other@cyvetech.com")
		try:
			n = note(owner="agent@cyvetech.com")
			as_user("other@cyvetech.com")
			notes.update_note("N1", pinned=1)
			self.assertEqual(n.pinned, 1)
			self.assertEqual(n.content, "old")
		finally:
			STATE["on_project"].discard("other@cyvetech.com")

	def test_an_edit_records_when_it_happened(self):
		n = note()
		as_user("agent@cyvetech.com")
		notes.update_note("N1", content="  new text  ")
		self.assertEqual(n.content, "new text")
		self.assertEqual(n.edited_on, "NOW")

	def test_deleting_someone_elses_note_is_refused(self):
		STATE["on_project"].add("other@cyvetech.com")
		try:
			note(owner="agent@cyvetech.com")
			as_user("other@cyvetech.com")
			with self.assertRaises(PermissionError_):
				notes.delete_note("N1")
			self.assertEqual(STATE["deleted"], [])
		finally:
			STATE["on_project"].discard("other@cyvetech.com")

	def test_the_author_can_delete_their_note(self):
		note()
		as_user("agent@cyvetech.com")
		notes.delete_note("N1")
		self.assertEqual(STATE["deleted"], [("HD Internal Note", "N1")])


class Content(Stubbed):
	def test_an_empty_note_is_refused(self):
		with self.assertRaises(Throw):
			notes.clean_content("   ")

	def test_an_overlong_note_is_refused(self):
		with self.assertRaises(Throw):
			notes.clean_content("x" * (notes.MAX_LENGTH + 1))

	def test_a_note_is_trimmed(self):
		self.assertEqual(notes.clean_content("  hi  "), "hi")


class Cascade(Stubbed):
	def setUp(self):
		super().setUp()

	def test_one_records_notes_go_with_it(self):
		notes.delete_notes_for("HD Addon Task", "TASK-1")
		self.assertEqual(
			STATE["deleted"],
			[("HD Internal Note", {"reference_doctype": "HD Addon Task", "reference_name": ["in", ["TASK-1"]]})],
		)

	def test_a_projects_tasks_notes_go_in_one_delete(self):
		notes.delete_notes_for("HD Addon Task", ["T1", "T2"])
		self.assertEqual(len(STATE["deleted"]), 1)
		self.assertEqual(STATE["deleted"][0][1]["reference_name"], ["in", ["T1", "T2"]])

	def test_nothing_to_delete_does_nothing(self):
		notes.delete_notes_for("HD Addon Task", [])
		self.assertEqual(STATE["deleted"], [])

	def test_before_its_migrate_the_cascade_stays_quiet(self):
		STATE["table"] = False
		notes.delete_notes_for("HD Project", "PROJ-1")
		self.assertEqual(STATE["deleted"], [])


if __name__ == "__main__":
	unittest.main()
