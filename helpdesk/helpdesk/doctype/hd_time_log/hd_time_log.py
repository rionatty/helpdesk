# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class HDTimeLog(Document):
	def validate(self):
		if flt(self.hours) <= 0:
			frappe.throw(_("Hours must be more than zero"))
