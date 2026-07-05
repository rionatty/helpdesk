import frappe


def execute():
	"""Stamp completed_on for tasks already marked Done. There's no historical
	completion timestamp, so use `modified` as the best available proxy — for a
	Done task, its last change is usually when it was completed."""
	if not frappe.db.table_exists("HD Addon Task"):
		return
	frappe.reload_doc("helpdesk", "doctype", "hd_addon_task")
	rows = frappe.get_all(
		"HD Addon Task",
		filters={"status": "Done", "completed_on": ["is", "not set"]},
		fields=["name", "modified"],
		ignore_permissions=True,
	)
	for r in rows:
		frappe.db.set_value(
			"HD Addon Task", r.name, "completed_on", r.modified, update_modified=False
		)
