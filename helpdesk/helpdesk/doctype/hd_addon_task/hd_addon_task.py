# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class HDAddonTask(Document):
	def validate(self):
		# A timed session has to end after it starts. Across days (a multi-day
		# session) the times are on different dates, so any order is fine.
		if self.start_time and self.end_time:
			from frappe.utils import get_time, getdate

			same_day = (
				not self.start_date
				or not self.end_date
				or getdate(self.start_date) == getdate(self.end_date)
			)
			if same_day and get_time(self.end_time) <= get_time(self.start_time):
				frappe.throw(frappe._("A session must end after it starts"))

	def on_update(self):
		# Sync the current milestone, and the previous one if it changed.
		self._sync_milestone(self.milestone)
		before = self.get_doc_before_save()
		if before and before.milestone and before.milestone != self.milestone:
			self._sync_milestone(before.milestone)
		# A UAT defect marked Done goes back to the client for a retest.
		if self.status == "Done" and before and before.status != "Done":
			from helpdesk.api.uat import defect_fixed

			defect_fixed(self.name)

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
