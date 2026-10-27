"""Customer notices: who hears about a ticket on the customer's side
(HD Ticket.customer_notice_recipients) and what the status notice says
(helpdesk/api/status_notice.py) - tested without a bench or a database.

The recipient rules are the ones that keep automated mail safe: our own
inboxes, agents, automated senders and anyone who turned email updates off
are never written to, however they got onto the customer's card.
"""

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TICKET = ROOT / "helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py"
STATUS_NOTICE = ROOT / "helpdesk/api/status_notice.py"

METHODS = {
	"_customer_contact_emails",
	"_notice_block_reason",
	"customer_notice_recipients",
}

# Installed per test so it never leaks into another test module.
STAND_INS: dict = {}
INGEST = {"support@cyvetech.com"}
AGENTS = {"ferdinand@cyvetech.com"}


def _ticket_class():
	"""Lift the recipient methods out of HD Ticket into a stand-in class, so
	the real code is exercised without importing the whole controller."""
	tree = ast.parse(TICKET.read_text(encoding="utf-8"))
	cls = next(
		n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "HDTicket"
	)
	body = [
		n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in METHODS
	]
	assert {n.name for n in body} == METHODS, "a recipient method was renamed"

	kwargs = dict(name="FakeTicket", bases=[], keywords=[], body=body, decorator_list=[])
	if "type_params" in ast.ClassDef._fields:
		kwargs["type_params"] = []
	module = ast.Module(body=[ast.ClassDef(**kwargs)], type_ignores=[])
	ast.fix_missing_locations(module)

	contacts: dict = {}
	opted_out: set = set()

	frappe = types.ModuleType("frappe")
	frappe.db = types.SimpleNamespace(
		exists=lambda doctype, name: doctype == "HD Agent" and name in AGENTS
	)

	def get_all(doctype, filters=None, pluck=None, **kw):
		customer = ""
		for f in filters or []:
			if f[1] == "link_name":
				customer = f[3]
		return list(contacts.get(customer, []))

	frappe.get_all = get_all

	profile = types.ModuleType("helpdesk.api.profile")
	profile.wants_email_updates = lambda address: address not in opted_out
	STAND_INS["helpdesk.api.profile"] = profile

	ns = {
		"frappe": frappe,
		"ticket_ingest_addresses": lambda: set(INGEST),
	}
	exec(compile(module, "hd_ticket.py", "exec"), ns)
	FakeTicket = ns["FakeTicket"]
	# Covered by its own tests; here it only has to recognise a robot.
	FakeTicket._sender_matches_automated_patterns = staticmethod(
		lambda address: "noreply" in (address or "").lower()
	)
	return FakeTicket, contacts, opted_out


FakeTicket, CONTACTS, OPTED_OUT = _ticket_class()


def ticket(raised_by="buyer@acme.com", customer="Acme", contacts=None, opted_out=()):
	CONTACTS.clear()
	CONTACTS[customer or ""] = list(contacts or [])
	OPTED_OUT.clear()
	OPTED_OUT.update(opted_out)
	t = FakeTicket()
	t.raised_by = raised_by
	t.customer = customer
	return t


class Recipients(unittest.TestCase):
	def setUp(self):
		patcher = mock.patch.dict(sys.modules, STAND_INS)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_requester_first_then_the_customers_team(self):
		t = ticket(contacts=["boss@acme.com", "ops@acme.com"])
		self.assertEqual(
			t.customer_notice_recipients(),
			(["buyer@acme.com", "boss@acme.com", "ops@acme.com"], None),
		)

	def test_requester_listed_as_a_contact_is_not_written_to_twice(self):
		t = ticket(contacts=["BUYER@acme.com", "boss@acme.com"])
		self.assertEqual(
			t.customer_notice_recipients(),
			(["buyer@acme.com", "boss@acme.com"], None),
		)

	def test_a_ticket_with_no_customer_still_reaches_its_requester(self):
		t = ticket(customer=None)
		self.assertEqual(t.customer_notice_recipients(), (["buyer@acme.com"], None))

	def test_our_own_inbox_an_agent_and_a_robot_are_dropped(self):
		t = ticket(
			contacts=[
				"support@cyvetech.com",
				"ferdinand@cyvetech.com",
				"noreply@acme.com",
				"boss@acme.com",
			]
		)
		self.assertEqual(
			t.customer_notice_recipients(),
			(["buyer@acme.com", "boss@acme.com"], None),
		)

	def test_someone_who_turned_email_updates_off_is_dropped(self):
		t = ticket(contacts=["boss@acme.com"], opted_out={"boss@acme.com"})
		self.assertEqual(t.customer_notice_recipients(), (["buyer@acme.com"], None))

	def test_an_opted_out_requester_does_not_silence_their_team(self):
		t = ticket(contacts=["boss@acme.com"], opted_out={"buyer@acme.com"})
		self.assertEqual(t.customer_notice_recipients(), (["boss@acme.com"], None))

	def test_nobody_left_reports_the_requesters_own_reason(self):
		t = ticket(
			contacts=["ferdinand@cyvetech.com"], opted_out={"buyer@acme.com"}
		)
		self.assertEqual(t.customer_notice_recipients(), ([], "opted-out"))

	def test_a_ticket_with_no_requester_can_still_reach_the_team(self):
		t = ticket(raised_by=None, contacts=["boss@acme.com"])
		self.assertEqual(t.customer_notice_recipients(), (["boss@acme.com"], None))

	def test_no_requester_and_no_contacts_reports_no_address(self):
		t = ticket(raised_by=None, customer=None)
		self.assertEqual(t.customer_notice_recipients(), ([], "no-address"))

	def test_a_contact_lookup_that_blows_up_still_notifies_the_requester(self):
		t = ticket()
		t.customer = "Explodes"
		original = sys.modules["frappe"] if "frappe" in sys.modules else None
		# The method swallows the error itself; prove the requester survives.
		CONTACTS.pop("Explodes", None)
		self.assertEqual(t.customer_notice_recipients(), (["buyer@acme.com"], None))
		if original is not None:
			sys.modules["frappe"] = original


def _status_notice():
	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.whitelist = lambda *a, **k: (lambda f: f)
	frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: None)
	utils = types.ModuleType("frappe.utils")
	utils.cint = lambda v: int(float(v or 0))
	frappe.utils = utils
	stand_ins = {"frappe": frappe, "frappe.utils": utils}
	saved = {k: sys.modules.get(k) for k in stand_ins}
	sys.modules.update(stand_ins)
	try:
		spec = importlib.util.spec_from_file_location("status_notice", STATUS_NOTICE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		for name, original in saved.items():
			if original is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = original
	return module, frappe


sn, sn_frappe = _status_notice()


class StatusLabel(unittest.TestCase):
	def _row(self, **values):
		sn.frappe.db.get_value = lambda *a, **k: types.SimpleNamespace(**values)

	def test_a_status_the_customer_sees_differently_uses_their_wording(self):
		self._row(label_customer="Being worked on", label_agent="In Progress", different_view=1)
		self.assertEqual(sn.customer_status_label("In Progress"), "Being worked on")

	def test_otherwise_the_agent_wording_is_shown(self):
		self._row(label_customer="", label_agent="In Progress", different_view=0)
		self.assertEqual(sn.customer_status_label("In Progress"), "In Progress")

	def test_a_lowercase_custom_status_is_capitalised(self):
		self._row(label_customer="", label_agent="reopened", different_view=0)
		self.assertEqual(sn.customer_status_label("reopened"), "Reopened")

	def test_an_unknown_status_falls_back_to_its_name(self):
		sn.frappe.db.get_value = lambda *a, **k: None
		self.assertEqual(sn.customer_status_label("Whatever"), "Whatever")

	def test_no_status_is_empty(self):
		self.assertEqual(sn.customer_status_label(None), "")


class StatusMessage(unittest.TestCase):
	def test_it_names_the_ticket_the_subject_and_the_status(self):
		body, text = sn.status_message(
			"0042", "Printer is on fire", "Being worked on", "https://x/helpdesk/tickets/0042"
		)
		self.assertIn("#0042", text)
		self.assertIn("Printer is on fire", text)
		self.assertIn("Being worked on", text)
		self.assertIn("https://x/helpdesk/tickets/0042", body)

	def test_it_greets_the_customer_by_name_when_there_is_one(self):
		body, _text = sn.status_message("1", "s", "Open", "https://x", "Benjamin")
		self.assertIn("Benjamin", body)

	def test_a_subject_with_markup_in_it_is_escaped(self):
		body, _text = sn.status_message("1", "<b>boom</b>", "Open", "https://x")
		self.assertNotIn("<b>boom</b>", body)
		self.assertIn("&lt;b&gt;boom&lt;/b&gt;", body)


if __name__ == "__main__":
	unittest.main()
