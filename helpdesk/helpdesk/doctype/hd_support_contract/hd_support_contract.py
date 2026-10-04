# Copyright (c) 2026, rionatty and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from helpdesk.api.contracts import validate_contract


class HDSupportContract(Document):
	def validate(self):
		validate_contract(self)
