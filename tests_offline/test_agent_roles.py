"""Moving an agent between tiers in Settings > Agents
(HD Agent.update_agent_role): Agent, Supervisor and Manager - tested
without a bench. Each move must leave exactly one tier behind, and never
strip a System Manager who was not a helpdesk manager."""

import ast
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

AGENT_PY = (
	Path(__file__).resolve().parents[1]
	/ "helpdesk/helpdesk/doctype/hd_agent/hd_agent.py"
)
SUPERVISOR = "Ticket Supervisor"

USERS: dict = {}
# Stand-ins for modules the function imports when it runs, installed per test
# so they never leak into another test module.
STAND_INS: dict = {}


class FakeUser:
	def __init__(self, name, roles):
		self.name = name
		self.roles = [types.SimpleNamespace(role=r) for r in roles]
		self.saves = 0

	def get(self, key):
		return self.roles

	def append_roles(self, *roles):
		have = {d.role for d in self.roles}
		for role in roles:
			if role not in have:
				self.roles.append(types.SimpleNamespace(role=role))

	def remove_roles(self, *roles):
		self.roles = [d for d in self.roles if d.role not in roles]
		self.save()

	def save(self):
		self.saves += 1
		USERS[self.name] = {d.role for d in self.roles}

	@property
	def role_set(self):
		return {d.role for d in self.roles}


def _load():
	tree = ast.parse(AGENT_PY.read_text(encoding="utf-8"))
	fn = next(
		n
		for n in tree.body
		if isinstance(n, ast.FunctionDef) and n.name == "update_agent_role"
	)
	fn.decorator_list = []
	module = ast.Module(body=[fn], type_ignores=[])
	ast.fix_missing_locations(module)

	frappe = types.ModuleType("frappe")
	frappe._ = lambda s: s
	frappe.only_for = lambda roles: None

	class ValidationError(Exception):
		pass

	def throw(message, exc=None):
		raise ValidationError(message)

	frappe.throw = throw
	frappe.db = types.SimpleNamespace(exists=lambda doctype, name: True)
	docs: dict = {}
	frappe.get_doc = lambda doctype, name: docs[name]
	frappe.get_roles = lambda name: set(USERS.get(name, set()))

	utils = types.ModuleType("helpdesk.utils")
	utils.TICKET_SUPERVISOR_ROLE = SUPERVISOR
	STAND_INS["helpdesk.utils"] = utils

	ns = {"frappe": frappe}
	exec(compile(module, "hd_agent.py", "exec"), ns)
	return ns["update_agent_role"], docs, ValidationError


update_agent_role, DOCS, ValidationError = _load()


def user(*roles):
	u = FakeUser("x@cyvetech.com", roles)
	DOCS[u.name] = u
	USERS[u.name] = set(roles)
	return u


class Tiers(unittest.TestCase):
	def setUp(self):
		patcher = mock.patch.dict(sys.modules, STAND_INS)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_agent_to_supervisor(self):
		u = user("Agent")
		update_agent_role(u.name, "Supervisor")
		self.assertEqual(u.role_set, {"Agent", SUPERVISOR})

	def test_manager_to_supervisor_drops_the_manager_roles(self):
		u = user("Agent", "Agent Manager", "System Manager")
		update_agent_role(u.name, "Supervisor")
		self.assertEqual(u.role_set, {"Agent", SUPERVISOR})

	def test_supervisor_to_agent_drops_the_supervisor_role(self):
		u = user("Agent", SUPERVISOR)
		update_agent_role(u.name, "Agent")
		self.assertEqual(u.role_set, {"Agent"})

	def test_supervisor_to_manager_is_one_tier(self):
		u = user("Agent", SUPERVISOR)
		update_agent_role(u.name, "Manager")
		self.assertEqual(u.role_set, {"Agent", "Agent Manager", "System Manager"})

	def test_manager_to_agent_drops_the_manager_roles(self):
		u = user("Agent", "Agent Manager", "System Manager")
		update_agent_role(u.name, "Agent")
		self.assertEqual(u.role_set, {"Agent"})

	def test_a_system_manager_who_is_not_a_helpdesk_manager_keeps_it(self):
		u = user("Agent", "System Manager", SUPERVISOR)
		update_agent_role(u.name, "Agent")
		self.assertEqual(u.role_set, {"Agent", "System Manager"})

	def test_every_move_saves_the_user_exactly_once(self):
		for start, target in [
			(("Agent",), "Supervisor"),
			(("Agent", "Agent Manager", "System Manager"), "Agent"),
			(("Agent", SUPERVISOR, "Agent Manager", "System Manager"), "Agent"),
			(("Agent",), "Manager"),
		]:
			u = user(*start)
			update_agent_role(u.name, target)
			self.assertEqual(u.saves, 1, f"{start} -> {target}")

	def test_an_unknown_role_is_refused(self):
		u = user("Agent")
		with self.assertRaises(ValidationError):
			update_agent_role(u.name, "Overlord")
		self.assertEqual(u.role_set, {"Agent"})


if __name__ == "__main__":
	unittest.main()
