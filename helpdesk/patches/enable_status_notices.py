"""The customer's team is told when their ticket moves - on by default.
Frappe does not write a new field's default into an existing Single, so it is
set here once."""

import frappe


def execute():
	frappe.db.set_single_value("HD Settings", "notify_customer_of_status", 1)
