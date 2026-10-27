# Copyright (c) 2026, rionatty and contributors
# Internal notes on projects and tasks: the team's own record - access
# details, decisions, context - kept apart from the description and the
# comment thread, which the customer sees on the portal.
#
# They live in their own doctype rather than a field on the project or task,
# because the portal is handed whole project records: a field there would
# travel with them. Plain agents get no direct permission on the doctype;
# everything goes through this API, which lets in only agents who can work on
# the record - a project's lead, members and managers; a task's people and
# its parent's members.

import frappe
from frappe import _
from frappe.utils import get_fullname, now_datetime

from helpdesk.utils import is_agent, is_agent_manager

NOTE_TARGETS = ("HD Project", "HD Addon Task")
MAX_LENGTH = 20000


def _assert_note_access(reference_doctype: str, reference_name: str) -> None:
	if reference_doctype not in NOTE_TARGETS:
		frappe.throw(_("Notes are not kept on {0}").format(reference_doctype))
	# Checked first: a task's own access check also lets its customer in.
	if not is_agent():
		frappe.throw(_("Only agents can read or write notes"), frappe.PermissionError)
	if reference_doctype == "HD Project":
		from helpdesk.api.project import _assert_agent_project

		_assert_agent_project(reference_name)
	else:
		from helpdesk.api.addon import _assert_task_access

		_assert_task_access(reference_name)


def can_change(note_owner: str, user: str | None = None) -> bool:
	"""Whether `user` may edit or delete a note: its author, or a manager.
	Pinning is open to anyone who can see the note."""
	user = user or frappe.session.user
	return user == note_owner or is_agent_manager(user)


def clean_content(content: str | None) -> str:
	content = (content or "").strip()
	if not content:
		frappe.throw(_("A note can't be empty"))
	if len(content) > MAX_LENGTH:
		frappe.throw(_("A note can be at most {0} characters").format(MAX_LENGTH))
	return content


def delete_notes_for(reference_doctype: str, names) -> None:
	"""Cascade for deletions that bypass document hooks. Quiet when the
	table isn't there yet (code deployed ahead of its migrate)."""
	if not names or not frappe.db.table_exists("HD Internal Note"):
		return
	names = names if isinstance(names, (list, tuple, set)) else [names]
	frappe.db.delete(
		"HD Internal Note",
		{"reference_doctype": reference_doctype, "reference_name": ["in", list(names)]},
	)


@frappe.whitelist()
def get_notes(reference_doctype: str, reference_name: str) -> list:
	"""The notes on a project or task, pinned first, newest first."""
	_assert_note_access(reference_doctype, reference_name)
	rows = frappe.get_all(
		"HD Internal Note",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		},
		fields=["name", "content", "pinned", "owner", "creation", "edited_on"],
		order_by="pinned desc, creation desc",
		ignore_permissions=True,
	)
	owners = list({r.owner for r in rows})
	agent_names = (
		{
			a.name: a.agent_name
			for a in frappe.get_all(
				"HD Agent",
				filters={"name": ["in", owners]},
				fields=["name", "agent_name"],
			)
		}
		if owners
		else {}
	)
	user = frappe.session.user
	for r in rows:
		r["author_name"] = agent_names.get(r.owner) or get_fullname(r.owner)
		r["can_change"] = can_change(r.owner, user)
	return rows


@frappe.whitelist()
def add_note(reference_doctype: str, reference_name: str, content: str) -> str:
	_assert_note_access(reference_doctype, reference_name)
	doc = frappe.get_doc(
		{
			"doctype": "HD Internal Note",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"content": clean_content(content),
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_note(name: str, content: str | None = None, pinned: int | None = None) -> bool:
	doc = frappe.get_doc("HD Internal Note", name)
	_assert_note_access(doc.reference_doctype, doc.reference_name)
	if content is not None:
		if not can_change(doc.owner):
			frappe.throw(
				_("Only the note's author or a manager can edit it"),
				frappe.PermissionError,
			)
		doc.content = clean_content(content)
		doc.edited_on = now_datetime()
	if pinned is not None:
		doc.pinned = 1 if frappe.utils.cint(pinned) else 0
	doc.save(ignore_permissions=True)
	return True


@frappe.whitelist()
def delete_note(name: str) -> bool:
	doc = frappe.get_doc("HD Internal Note", name)
	_assert_note_access(doc.reference_doctype, doc.reference_name)
	if not can_change(doc.owner):
		frappe.throw(
			_("Only the note's author or a manager can delete it"),
			frappe.PermissionError,
		)
	frappe.delete_doc("HD Internal Note", name, ignore_permissions=True)
	return True
