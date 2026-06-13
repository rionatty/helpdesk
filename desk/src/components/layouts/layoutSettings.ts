import LucideBookOpen from "~icons/lucide/book-open";
import LucideContact2 from "~icons/lucide/contact-2";
import LucideTicket from "~icons/lucide/ticket";
import LucideLayoutDashboard from "~icons/lucide/layout-dashboard";
import LucideFolderKanban from "~icons/lucide/folder-kanban";
import LucideLayoutTemplate from "~icons/lucide/layout-template";
import LucidePackage from "~icons/lucide/package";
import { OrganizationsIcon } from "../icons";
import PhoneIcon from "../icons/PhoneIcon.vue";
import LucideHome from "~icons/lucide/home";
import { __ } from "@/translation";

export const agentPortalSidebarOptions = [
  {
    label: __("Home"),
    icon: LucideHome,
    to: "Home",
  },
  {
    label: __("Dashboard"),
    icon: LucideLayoutDashboard,
    to: "Dashboard"
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsAgent",
  },
  {
    label: __("Projects"),
    icon: LucideFolderKanban,
    to: "ProjectsAgent",
  },
  {
    label: __("Templates"),
    icon: LucideLayoutTemplate,
    to: "ProjectTemplates",
  },
  {
    label: __("Add-ons"),
    icon: LucidePackage,
    to: "AddonsAgent",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "AgentKnowledgeBase",
  },
  {
    label: "Customers",
    icon: OrganizationsIcon,
    to: "CustomerList",
  },
  {
    label: __("Contacts"),
    icon: LucideContact2,
    to: "ContactList",
  },
  {
    label: __("Call Logs"),
    icon: PhoneIcon,
    to: "CallLogs",
  },
];

export const customerPortalSidebarOptions = [
  {
    label: __("Home"),
    icon: LucideHome,
    to: "CustomerHome",
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsCustomer",
  },
  {
    label: __("Projects"),
    icon: LucideFolderKanban,
    to: "ProjectsCustomer",
  },
  {
    label: __("Add-ons"),
    icon: LucidePackage,
    to: "AddonsCustomer",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "CustomerKnowledgeBase",
  },
];
