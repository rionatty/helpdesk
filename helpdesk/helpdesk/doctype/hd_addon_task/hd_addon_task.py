# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class HDAddonTask(Document):
	def on_update(self):
		# Sync the current milestone, and the previous one if it changed.
		self._sync_milestone(self.milestone)
		before = self.get_doc_before_save()
		if before and before.milestone and before.milestone != self.milestone:
			self._sync_milestone(before.milestone)

	def after_delete(self):
		self._sync_milestone(self.milestone)

	@staticmethod
	def _sync_milestone(milestone: str | None):
		"""Auto-track milestone completion from its tasks.

		All tasks Done -> Completed (+ completed_on). Any task not Done on a
		Completed milestone -> back to In Progress. Upcoming/Missed are left
		alone until work actually closes out.
		"""
		if not milestone or not frappe.db.exists("HD Milestone", milestone):
			return
		statuses = frappe.get_all(
			"HD Addon Task", filters={"milestone": milestone}, pluck="status"
		)
		current = frappe.db.get_value("HD Milestone", milestone, "status")
		if statuses and all(s == "Done" for s in statuses):
			if current != "Completed":
				frappe.db.set_value(
					"HD Milestone",
					milestone,
					{"status": "Completed", "completed_on": now_datetime()},
				)
		elif current == "Completed":
			frappe.db.set_value(
				"HD Milestone",
				milestone,
				{"status": "In Progress", "completed_on": None},
			)
