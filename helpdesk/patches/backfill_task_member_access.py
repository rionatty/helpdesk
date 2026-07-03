import frappe


def execute():
	"""Grant project/add-on membership to agents who are already the assignee
	or reviewer of a task, so existing assignments become visible under the new
	assignment-scoped access rules (assigning work grants access to its
	context). Standalone tasks have no parent to join and are skipped."""
	if not frappe.db.table_exists("HD Addon Task"):
		return

	tasks = frappe.get_all(
		"HD Addon Task",
		filters=[["project", "is", "set"]],
		fields=["project", "addon", "assigned_to", "reviewer"],
		ignore_permissions=True,
	) + frappe.get_all(
		"HD Addon Task",
		filters=[["addon", "is", "set"]],
		fields=["project", "addon", "assigned_to", "reviewer"],
		ignore_permissions=True,
	)

	seen: set = set()
	for t in tasks:
		people = [p for p in (t.assigned_to, t.reviewer) if p]
		if not people:
			continue
		if t.project:
			doctype, field, parent = "HD Project Member", "project", t.project
		elif t.addon:
			doctype, field, parent = "HD Addon Member", "addon", t.addon
		else:
			continue
		for agent in people:
			key = (doctype, parent, agent)
			if key in seen:
				continue
			seen.add(key)
			if not frappe.db.exists("HD Agent", agent):
				continue
			if frappe.db.exists(doctype, {field: parent, "agent": agent}):
				continue
			frappe.get_doc(
				{"doctype": doctype, field: parent, "agent": agent}
			).insert(ignore_permissions=True)
