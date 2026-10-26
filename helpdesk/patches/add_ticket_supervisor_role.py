"""The Ticket Supervisor role: sees every ticket without running the
helpdesk. Created here for sites that already exist, and the client
restriction is switched on at the same time - agents then see the clients
they are assigned to, while managers and supervisors still see everything.

Frappe does not write a new Check field's default into an existing Single,
so the setting is set explicitly.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

from helpdesk.utils import TICKET_SUPERVISOR_ROLE


def execute():
	if not frappe.db.exists("Role", TICKET_SUPERVISOR_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": TICKET_SUPERVISOR_ROLE,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)

	# Reading the queue is the point of the role; anything they change they
	# change through their own Agent role.
	add_permission("HD Ticket", TICKET_SUPERVISOR_ROLE, 0)
	for permission in ("read", "report", "export", "share"):
		update_permission_property(
			"HD Ticket", TICKET_SUPERVISOR_ROLE, 0, permission, 1
		)

	frappe.db.set_single_value("HD Settings", "restrict_tickets_by_customer", 1)
