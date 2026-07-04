import frappe


def execute():
	"""Rename the task status 'Blocked' to 'Pending' on existing rows.
	'Postponed' is a new status with no rows to migrate."""
	for doctype in ("HD Addon Task", "HD Project Template Task"):
		if not frappe.db.table_exists(doctype):
			continue
		frappe.db.set_value(
			doctype,
			{"status": "Blocked"},
			"status",
			"Pending",
			update_modified=False,
		)
