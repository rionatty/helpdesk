"""Who can see which ticket (HD Ticket has_permission / permission_query),
tested without a bench or a database.

The rules under test:
- Administrator, Agent Managers and Ticket Supervisors see every ticket.
- With "Restrict tickets by assigned client" on, a plain agent sees the
  clients they are assigned to (through projects and add-ons), tickets
  assigned to them personally, and tickets not yet tagged to a client.
- With it off (and the team restriction off), agents see everything, as
  they always did.
- A customer's contact sees their own tickets and their company's.
"""

import ast
import json
import types
import unittest
from pathlib import Path

TICKET = (
	Path(__file__).resolve().parents[1]
	/ "helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py"
)

AGENTS = {"plain@cyvetech.com", "boss@cyvetech.com", "watcher@cyvetech.com"}
MANAGERS = {"boss@cyvetech.com"}
SUPERVISORS = {"watcher@cyvetech.com"}
CLIENTS_OF = {"plain@cyvetech.com": {"Acme"}}
CONTACT_OF = {"buyer@acme.com": ["Acme"]}
SETTINGS: dict = {}


def _load():
	tree = ast.parse(TICKET.read_text(encoding="utf-8"))
	funcs = [
		n
		for n in tree.body
		if isinstance(n, ast.FunctionDef)
		and n.name in ("has_permission", "permission_query")
	]
	assert {f.name for f in funcs} == {"has_permission", "permission_query"}
	module = ast.Module(body=funcs, type_ignores=[])
	ast.fix_missing_locations(module)

	frappe = types.ModuleType("frappe")
	frappe.session = types.SimpleNamespace(user="Guest")
	frappe.db = types.SimpleNamespace(
		get_single_value=lambda doctype, field: SETTINGS.get(field, 0),
		escape=lambda value: "'" + str(value).replace("'", "''") + "'",
		exists=lambda *a, **k: False,
	)
	frappe.get_all = lambda *a, **k: []

	ns = {
		"frappe": frappe,
		"json": json,
		"is_admin": lambda user=None: user == "Administrator",
		"is_agent": lambda user=None: user in AGENTS,
		"is_agent_manager": lambda user=None: user in MANAGERS,
		"is_ticket_supervisor": lambda user=None: user in SUPERVISORS,
		"agent_customers": lambda user=None: set(CLIENTS_OF.get(user, set())),
		"get_customer": lambda user: list(CONTACT_OF.get(user, [])),
		"get_agents_team": lambda: [],
	}
	exec(compile(module, "hd_ticket.py", "exec"), ns)
	return ns["has_permission"], ns["permission_query"]


has_permission, permission_query = _load()


class Doc(dict):
	__getattr__ = dict.get


def ticket(customer=None, assign=None, raised_by="someone@else.com", contact=None):
	return Doc(
		customer=customer,
		_assign=json.dumps(assign) if assign else None,
		raised_by=raised_by,
		contact=contact,
		owner="Administrator",
		agent_group=None,
	)


def restricted(on=True):
	SETTINGS.clear()
	SETTINGS["restrict_tickets_by_customer"] = 1 if on else 0


class SingleTicket(unittest.TestCase):
	def test_administrator_sees_everything(self):
		restricted()
		self.assertTrue(has_permission(ticket("Globex"), "Administrator"))

	def test_an_agent_manager_sees_every_client(self):
		restricted()
		self.assertTrue(has_permission(ticket("Globex"), "boss@cyvetech.com"))

	def test_a_ticket_supervisor_sees_every_client(self):
		restricted()
		self.assertTrue(has_permission(ticket("Globex"), "watcher@cyvetech.com"))

	def test_an_agent_sees_a_client_they_are_assigned_to(self):
		restricted()
		self.assertTrue(has_permission(ticket("Acme"), "plain@cyvetech.com"))

	def test_an_agent_does_not_see_another_clients_ticket(self):
		restricted()
		self.assertFalse(has_permission(ticket("Globex"), "plain@cyvetech.com"))

	def test_an_agent_sees_a_ticket_assigned_to_them_on_any_client(self):
		restricted()
		self.assertTrue(
			has_permission(
				ticket("Globex", assign=["plain@cyvetech.com"]), "plain@cyvetech.com"
			)
		)

	def test_an_untagged_ticket_is_open_to_every_agent_for_triage(self):
		restricted()
		self.assertTrue(has_permission(ticket(None), "plain@cyvetech.com"))

	def test_with_the_restriction_off_agents_see_everything_as_before(self):
		restricted(on=False)
		self.assertTrue(has_permission(ticket("Globex"), "plain@cyvetech.com"))

	def test_a_contact_sees_their_companys_ticket(self):
		restricted()
		self.assertTrue(has_permission(ticket("Acme"), "buyer@acme.com"))

	def test_a_contact_does_not_see_another_companys_ticket(self):
		restricted()
		self.assertFalse(has_permission(ticket("Globex"), "buyer@acme.com"))

	def test_a_contact_sees_a_ticket_they_raised(self):
		restricted()
		self.assertTrue(
			has_permission(ticket("Globex", raised_by="buyer@acme.com"), "buyer@acme.com")
		)


class ListFilter(unittest.TestCase):
	def test_administrator_is_unfiltered(self):
		restricted()
		self.assertIsNone(permission_query("Administrator"))

	def test_managers_and_supervisors_are_unfiltered(self):
		restricted()
		self.assertIsNone(permission_query("boss@cyvetech.com"))
		self.assertIsNone(permission_query("watcher@cyvetech.com"))

	def test_a_restricted_agent_gets_their_clients_their_tickets_and_untagged(self):
		restricted()
		q = permission_query("plain@cyvetech.com")
		self.assertIn("`tabHD Ticket`.customer in ('Acme')", q)
		self.assertIn("JSON_SEARCH(`tabHD Ticket`._assign, 'all', 'plain@cyvetech.com')", q)
		self.assertIn("`tabHD Ticket`.customer is null", q)
		self.assertNotIn("Globex", q)

	def test_an_agent_with_no_clients_gets_no_empty_in_clause(self):
		restricted()
		AGENTS.add("new@cyvetech.com")
		try:
			q = permission_query("new@cyvetech.com")
		finally:
			AGENTS.discard("new@cyvetech.com")
		self.assertNotIn("in ()", q)
		self.assertIn("customer is null", q)

	def test_with_the_restriction_off_agents_are_unfiltered_as_before(self):
		restricted(on=False)
		self.assertIsNone(permission_query("plain@cyvetech.com"))

	def test_a_contact_is_held_to_their_own_company(self):
		restricted()
		q = permission_query("buyer@acme.com")
		self.assertIn("`tabHD Ticket`.customer='Acme'", q)
		self.assertNotIn("customer is null", q)


if __name__ == "__main__":
	unittest.main()
