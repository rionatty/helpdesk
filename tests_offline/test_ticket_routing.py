"""New-ticket routing (helpdesk/helpdesk/utils/ticket_routing.py), tested
against a stand-in for frappe with an in-memory dataset - no bench needed.

Covers every routing step, every fall-through, and the guarantee that a
routing failure degrades to "everyone" instead of losing the ticket.
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "helpdesk/helpdesk/utils/ticket_routing.py"

DATA: dict = {}
LOGGED: list = []
FAIL = {"on": False}


def _match(row, filters):
	for field, cond in (filters or {}).items():
		val = row.get(field)
		if isinstance(cond, list):
			op, arg = cond
			if op == "in" and val not in arg:
				return False
			if op == "not in" and val in arg:
				return False
			if op == "is" and arg == "set" and not val:
				return False
		elif val != cond:
			return False
	return True


def _get_all(doctype, filters=None, pluck=None, **_):
	if FAIL["on"]:
		raise RuntimeError("simulated database failure")
	rows = [r for r in DATA.get(doctype, []) if _match(r, filters)]
	return [r.get(pluck) for r in rows] if pluck else rows


class _Doc:
	def __init__(self, row):
		self.__dict__.update(row)
		self.agents = [types.SimpleNamespace(agent=a) for a in row.get("agents", [])]


def _load_module():
	fake = types.ModuleType("frappe")
	fake.get_all = _get_all
	fake.db = types.SimpleNamespace(
		get_value=lambda dt, filters, field: next(
			(r[field] for r in DATA.get(dt, []) if _match(r, filters)), None
		)
	)
	fake.get_doc = lambda dt, name: _Doc(next(r for r in DATA[dt] if r["name"] == name))
	fake.log_error = lambda title=None, **_: LOGGED.append(title)
	saved = sys.modules.get("frappe")
	sys.modules["frappe"] = fake
	try:
		spec = importlib.util.spec_from_file_location("ticket_routing_under_test", MODULE)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		# The module keeps its own reference; don't leak the fake to other tests.
		if saved is None:
			sys.modules.pop("frappe", None)
		else:
			sys.modules["frappe"] = saved
	return module


routing = _load_module()


class Ticket(dict):
	__getattr__ = dict.get


DATA.update(
	{
		"HD Agent": [
			{"name": n, "is_active": 0 if n == "gone@x" else 1}
			for n in ["a1", "a2", "lead@x", "inbox1", "inbox2", "del1", "addon1", "gone@x"]
		],
		"HD Project": [
			{"name": "P-LUUKA", "customer": "Luuka", "status": "Active", "lead": "lead@x"},
			{"name": "P-EMPTY", "customer": "Empty", "status": "Active", "lead": None},
			{"name": "P-OLD", "customer": "Live", "status": "Completed", "lead": None},
			{"name": "P-CANCEL", "customer": "Luuka", "status": "Cancelled", "lead": None},
			{"name": "P-GONE", "customer": "Ghost", "status": "Active", "lead": None},
			{"name": "P-MIX-OPEN", "customer": "Mix", "status": "Planned", "lead": None},
			{"name": "P-MIX-DONE", "customer": "Mix", "status": "Completed", "lead": None},
		],
		"HD Project Member": [
			{"project": "P-LUUKA", "agent": "a1"},
			{"project": "P-LUUKA", "agent": "a2"},
			{"project": "P-OLD", "agent": "del1"},
			{"project": "P-CANCEL", "agent": "inbox2"},  # must never leak in
			{"project": "P-GONE", "agent": "gone@x"},  # inactive only
			{"project": "P-MIX-OPEN", "agent": "a1"},
			{"project": "P-MIX-DONE", "agent": "del1"},  # open team wins over this
		],
		"HD Addon": [
			{"name": "AD-1", "customer": "Addy", "status": "Active"},
			{"name": "AD-RET", "customer": "Retro", "status": "Retired"},
		],
		"HD Addon Member": [
			{"addon": "AD-1", "agent": "addon1"},
			{"addon": "AD-RET", "agent": "addon1"},
		],
		"HD Inbox Routing": [
			{"name": "r1", "email_account": "muted@", "notify": "No one", "agents": []},
			{
				"name": "r2",
				"email_account": "finance@",
				"notify": "Selected agents",
				"agents": ["inbox1", "inbox2"],
			},
			{
				"name": "r3",
				"email_account": "deadsel@",
				"notify": "Selected agents",
				"agents": ["gone@x"],
			},
			{"name": "r4", "email_account": "auto@", "notify": "Automatic", "agents": []},
		],
	}
)

LUUKA_TEAM = ["a1", "a2", "lead@x"]

CASES = [
	("muted inbox emails nobody, even for a known client",
	 Ticket(email_account="muted@", customer="Luuka"), "no_one", []),
	("explicit project -> members + lead",
	 Ticket(project="P-LUUKA"), "project", LUUKA_TEAM),
	("explicit project beats the inbox's chosen agents",
	 Ticket(project="P-LUUKA", email_account="finance@"), "project", LUUKA_TEAM),
	("explicit add-on -> its members",
	 Ticket(addon="AD-1"), "project", ["addon1"]),
	("project nobody is on falls through to the inbox rule",
	 Ticket(project="P-EMPTY", email_account="finance@"), "inbox", ["inbox1", "inbox2"]),
	("project with only an inactive member falls through",
	 Ticket(project="P-GONE", email_account="finance@"), "inbox", ["inbox1", "inbox2"]),
	("inbox 'Selected agents' -> exactly them",
	 Ticket(email_account="finance@", customer="Luuka"), "inbox", ["inbox1", "inbox2"]),
	("inbox whose chosen agents are all inactive falls through to the client",
	 Ticket(email_account="deadsel@", customer="Luuka"), "client", LUUKA_TEAM),
	("emailed ticket, no rule: client's open project team, cancelled excluded",
	 Ticket(email_account="unconfigured@", customer="Luuka"), "client", LUUKA_TEAM),
	("'Automatic' inbox behaves like no rule",
	 Ticket(email_account="auto@", customer="Luuka"), "client", LUUKA_TEAM),
	("client with only a delivered project -> that team (post go-live)",
	 Ticket(customer="Live"), "client", ["del1"]),
	("open project team wins over the delivered one",
	 Ticket(customer="Mix"), "client", ["a1"]),
	("client's active add-on team counts",
	 Ticket(customer="Addy"), "client", ["addon1"]),
	("retired add-on does not count -> everyone",
	 Ticket(customer="Retro"), "everyone", []),
	("client with no projects -> everyone",
	 Ticket(customer="Nobody"), "everyone", []),
	("portal ticket with nothing to go on -> everyone",
	 Ticket(), "everyone", []),
]


class TestTicketRouting(unittest.TestCase):
	def test_routing_rules(self):
		for desc, ticket, scope, agents in CASES:
			with self.subTest(desc):
				self.assertEqual(routing.route_new_ticket(ticket), (scope, sorted(agents)))

	def test_failure_degrades_to_everyone_and_is_logged(self):
		FAIL["on"] = True
		try:
			result = routing.route_new_ticket(Ticket(name="T-1", project="P-LUUKA"))
		finally:
			FAIL["on"] = False
		self.assertEqual(result, ("everyone", []))
		self.assertTrue(LOGGED and "T-1" in LOGGED[-1])


if __name__ == "__main__":
	unittest.main()
