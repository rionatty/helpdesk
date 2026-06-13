# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HDProjectTemplate(Document):
	def validate(self):
		titles = {(m.title or "").strip() for m in (self.milestones or [])}
		for t in self.tasks or []:
			mt = (t.milestone_title or "").strip()
			if mt and mt not in titles:
				frappe.throw(
					_("Task '{0}' references unknown milestone '{1}'").format(
						t.subject, mt
					)
				)
