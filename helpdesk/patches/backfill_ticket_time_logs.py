"""Hours already typed on ticket subtasks become time-log entries, so each
ticket's time list and the clients' support-hours balances start complete.

An entry is dated the day its subtask was last changed: the closest record
there is of when the work was done. Subtasks that already have entries are
left alone, so running this twice changes nothing."""

import frappe
from frappe.utils import flt, getdate


def execute():
	rows = frappe.get_all(
		"HD Ticket Subtask",
		filters={"hours_spent": [">", 0]},
		fields=["name", "ticket", "hours_spent", "modified", "owner", "assigned_to"],
		limit_page_length=0,
	)
	if not rows:
		return
	done = set(frappe.get_all("HD Time Log", filters={"subtask": ["is", "set"]}, pluck="subtask"))
	customers = dict(
		frappe.get_all(
			"HD Ticket",
			filters={"name": ["in", list({r.ticket for r in rows if r.ticket})]},
			fields=["name", "customer"],
			as_list=True,
		)
	)
	for r in rows:
		if r.name in done or r.ticket not in customers:
			continue
		who = r.assigned_to if r.assigned_to and frappe.db.exists("User", r.assigned_to) else r.owner
		try:
			doc = frappe.get_doc(
				{
					"doctype": "HD Time Log",
					"customer": customers.get(r.ticket),
					"ticket": r.ticket,
					"subtask": r.name,
					"date": getdate(r.modified),
					"hours": flt(r.hours_spent),
					"billable": 1,
					"logged_by": who,
				}
			)
			doc.flags.ignore_links = True
			doc.insert(ignore_permissions=True)
		except Exception:
			# A bad row must not stop the migration; it is recorded instead.
			frappe.log_error(title=f"Support hours backfill: skipped subtask {r.name}")
