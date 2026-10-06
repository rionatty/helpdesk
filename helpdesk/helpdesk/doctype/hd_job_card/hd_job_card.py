# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from helpdesk.api.job_card import validate_card


class HDJobCard(Document):
	def validate(self):
		validate_card(self)
