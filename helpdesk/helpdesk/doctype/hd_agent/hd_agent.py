# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HDAgent(Document):
    def before_save(self):
        old_doc = self.get_doc_before_save()
        if old_doc and old_doc.agent_name != self.agent_name:
            if self.agent_name:
                agent_name = self.agent_name.split()
                frappe.set_value(
                    "User",
                    self.user,
                    {
                        "first_name": agent_name[0],
                        "last_name": " ".join(agent_name[1:]),
                    },
                )
            else:
                self.agent_name = frappe.get_value("User", self.user, "full_name")

        if old_doc and old_doc.user_image != self.user_image:
            frappe.set_value("User", self.user, "user_image", self.user_image)

        if self.name == self.user:
            return

        self.name = self.user
        self.set_user_roles()

    def set_user_roles(self):
        user = frappe.get_doc("User", self.user)
        for role in ["Agent"]:
            user.append("roles", {"role": role})
        user.save(ignore_permissions=True)


@frappe.whitelist()
def update_agent_role(user: str, new_role: str):
    """
    Move an agent between the tiers: Agent, Supervisor (an agent who sees
    every ticket, whichever client it belongs to) and Manager.
    """
    frappe.only_for(("Agent Manager", "System Manager"))

    from helpdesk.utils import TICKET_SUPERVISOR_ROLE

    if new_role not in ("Agent", "Supervisor", "Manager"):
        frappe.throw(frappe._("Unknown role: {0}").format(new_role))

    user_doc = frappe.get_doc("User", user)
    current = set(frappe.get_roles(user_doc.name))
    to_remove = []

    if new_role == "Manager":
        user_doc.append_roles("Agent Manager", "System Manager")
        # A manager already sees everything; one tier at a time.
        to_remove = [TICKET_SUPERVISOR_ROLE]
    elif new_role == "Supervisor":
        if not frappe.db.exists("Role", TICKET_SUPERVISOR_ROLE):
            from helpdesk.setup.install import add_ticket_supervisor_role

            add_ticket_supervisor_role()
        user_doc.append_roles("Agent", TICKET_SUPERVISOR_ROLE)
        if "Agent Manager" in current:
            to_remove = ["Agent Manager", "System Manager"]
    else:
        user_doc.append_roles("Agent")
        to_remove = [TICKET_SUPERVISOR_ROLE]
        if "Agent Manager" in current:
            to_remove += ["Agent Manager", "System Manager"]

    to_remove = [role for role in to_remove if role in current]
    if to_remove:
        user_doc.remove_roles(*to_remove)  # saves the user, appends included
    else:
        user_doc.save()
