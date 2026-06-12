import frappe


def execute():
	"""Backfill project_type on HD Project rows created before the field existed.
	Everything pre-dating internal projects was a customer engagement."""
	if not frappe.db.table_exists("HD Project"):
		return
	frappe.reload_doc("helpdesk", "doctype", "hd_project")
	frappe.db.set_value(
		"HD Project",
		{"project_type": ["in", ["", None]]},
		"project_type",
		"Customer",
		update_modified=False,
	)
