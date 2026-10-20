"""Customers are told who is handling their ticket and when it should be
resolved - on by default. Frappe does not write a new field's default into
an existing Single, so it is set here once."""

import frappe


def execute():
	frappe.db.set_single_value("HD Settings", "notify_customer_of_assignment", 1)
