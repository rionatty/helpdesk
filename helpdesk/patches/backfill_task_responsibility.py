import frappe


def execute():
	"""Backfill responsibility on tasks and subtasks created before the field
	existed. A Select default only applies to new rows, so everything already in
	the table is NULL — and all of it predates the us/client split, when every
	task was ours to do."""
	for doctype, doctype_dir in (
		("HD Addon Task", "hd_addon_task"),
		("HD Task Subtask", "hd_task_subtask"),
		("HD Ticket Subtask", "hd_ticket_subtask"),
	):
		if not frappe.db.table_exists(doctype):
			continue
		frappe.reload_doc("helpdesk", "doctype", doctype_dir)
		frappe.db.set_value(
			doctype,
			{"responsibility": ["in", ["", None]]},
			"responsibility",
			"Us",
			update_modified=False,
		)
