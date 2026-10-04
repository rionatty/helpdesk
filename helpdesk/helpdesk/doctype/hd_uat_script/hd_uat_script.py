# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from helpdesk.api.uat import validate_script


class HDUATScript(Document):
	def validate(self):
		validate_script(self)
