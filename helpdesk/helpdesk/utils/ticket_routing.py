# Who hears about a new ticket.
#
# Decides which agents get the new-ticket email and which agents auto-
# assignment may choose from, so a client's ticket reaches the people
# responsible for that client instead of every agent on the platform:
#
#   1. The ticket's inbox is set to "No one"   -> nobody is emailed.
#   2. The ticket names a project or add-on    -> that project's team.
#   3. The inbox is set to "Selected agents"   -> those agents.
#   4. The client has projects or add-ons      -> their team: the ones in
#                                                 progress first, else the
#                                                 projects already delivered.
#   5. Otherwise                               -> everyone, as before.
#
# A step that finds no active agent falls through to the next, so a project
# nobody is assigned to can never swallow a ticket.

import frappe

OPEN_PROJECT_STATUSES = ["Planned", "Active", "On Hold"]
CLOSED_ADDON_STATUSES = ["Retired"]

# Scopes that name an exact audience (as opposed to "no_one" / "everyone").
SCOPED = ("project", "inbox", "client")


def inbox_rule(email_account: str | None):
	"""The routing rule saved for an inbox, or None when it has none."""
	if not email_account:
		return None
	try:
		name = frappe.db.get_value(
			"HD Inbox Routing", {"email_account": email_account}, "name"
		)
	except Exception:
		# Table may not exist yet (pre-migrate): behave as if unconfigured.
		return None
	return frappe.get_doc("HD Inbox Routing", name) if name else None


def _active(agents) -> set:
	agents = {a for a in agents if a}
	if not agents:
		return set()
	return set(
		frappe.get_all(
			"HD Agent",
			filters={"name": ["in", list(agents)], "is_active": 1},
			pluck="name",
		)
	)


def _project_team(projects: list) -> set:
	if not projects:
		return set()
	team = set(
		frappe.get_all(
			"HD Project Member", filters={"project": ["in", projects]}, pluck="agent"
		)
	)
	team |= set(
		frappe.get_all(
			"HD Project",
			filters={"name": ["in", projects], "lead": ["is", "set"]},
			pluck="lead",
		)
	)
	return team


def _addon_team(addons: list) -> set:
	if not addons:
		return set()
	return set(
		frappe.get_all(
			"HD Addon Member", filters={"addon": ["in", addons]}, pluck="agent"
		)
	)


def _client_team(customer: str) -> set:
	"""Agents on the client's projects and add-ons. Work in progress wins;
	only when none of it has anyone do the delivered projects count, which is
	what keeps post-go-live support with the team that implemented it."""
	open_projects = frappe.get_all(
		"HD Project",
		filters={"customer": customer, "status": ["in", OPEN_PROJECT_STATUSES]},
		pluck="name",
	)
	addons = frappe.get_all(
		"HD Addon",
		filters={"customer": customer, "status": ["not in", CLOSED_ADDON_STATUSES]},
		pluck="name",
	)
	team = _active(_project_team(open_projects) | _addon_team(addons))
	if team:
		return team
	delivered = frappe.get_all(
		"HD Project",
		filters={"customer": customer, "status": "Completed"},
		pluck="name",
	)
	return _active(_project_team(delivered))


def route_new_ticket(ticket) -> tuple[str, list]:
	"""(scope, agents) for a new ticket. scope is one of:
	  "no_one"                      the inbox is muted: email nobody
	  "project" / "inbox" / "client" email exactly `agents`
	  "everyone"                    nothing narrower applies: caller's default
	Never raises: a routing failure is logged and falls back to "everyone",
	so a bug here can cost precision but never a missed ticket."""
	try:
		rule = inbox_rule(ticket.get("email_account"))
		if rule and rule.notify == "No one":
			return "no_one", []

		named = set()
		if ticket.get("project"):
			named |= _project_team([ticket.project])
		if ticket.get("addon"):
			named |= _addon_team([ticket.addon])
		named = _active(named)
		if named:
			return "project", sorted(named)

		if rule and rule.notify == "Selected agents":
			chosen = _active({row.agent for row in rule.agents})
			if chosen:
				return "inbox", sorted(chosen)

		if ticket.get("customer"):
			team = _client_team(ticket.customer)
			if team:
				return "client", sorted(team)
	except Exception:
		frappe.log_error(title=f"New-ticket routing failed for {ticket.get('name')}")
	return "everyone", []
