# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from helpdesk.api.contracts import sync_subtask_hours


class HDTicketSubtask(Document):
	def on_update(self):
		# Hours typed on a subtask count toward the client's support hours.
		# That bookkeeping must never stop the subtask itself from saving.
		frappe.db.savepoint("hd_subtask_time")
		try:
			sync_subtask_hours(self)
		except Exception:
			frappe.db.rollback(save_point="hd_subtask_time")
			frappe.log_error(title=f"Support hours: could not record time for subtask {self.name}")

	def on_trash(self):
		if frappe.db.table_exists("HD Time Log"):
			frappe.db.delete("HD Time Log", {"subtask": self.name})
