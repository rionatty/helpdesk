# Projects & Add-ons

Per-customer **Projects** (client engagements) and **Add-ons** (deployed
apps/modules), managed by agents and surfaced to customers in the portal.

This document is the living spec — keep it in sync with the implementation.

## Concepts

- **Project** — a client engagement/implementation for one customer. Has a
  status, timeline, progress %, owning team, description, a discussion thread
  (customer + agents), and any number of linked tickets.
- **Add-on** — an app/module a customer runs (e.g. Agriculture, Efris, Stock
  Addon). Has a status, version, activation/renewal dates, notes. Customer-facing
  view is read-only.

## Data model

| DocType | Key fields | Notes |
|---|---|---|
| `HD Project` | `project_name`, `customer` (→ HD Customer), `status` (Planned/Active/On Hold/Completed/Cancelled), `team` (→ HD Team), `start_date`, `end_date`, `progress` (0–100), `description` | autoname `HD-PROJ-.#####` |
| `HD Add-on` (`HD Addon`) | `addon_name`, `customer`, `status` (Active/Trial/Suspended/Retired), `version`, `activated_on`, `renewal_date`, `notes` | autoname `HD-ADDON-.#####` |
| `HD Project Comment` | `project` (→ HD Project), `content` | one row per comment; `owner`/`creation` track author/time |
| `HD Ticket` | **new** `project` (→ HD Project) | optional; tags a ticket to a project |

## Access model

The portal user → company link is **User → Contact (by email) → HD Customer
(Dynamic Link)**, resolved by `helpdesk.utils.get_customer`.

- **Agents** manage everything (create/edit/delete projects & add-ons).
- **Customers** see only their own company's projects & add-ons, and may
  **comment** on their projects (collaborate). Add-ons are read-only.

All API reads/writes verify access explicitly and then use `ignore_permissions`,
so portal users need no direct doctype permissions (same pattern as subtasks /
participants).

## APIs

`helpdesk/api/project.py`
- `get_projects(customer=None)` — agents: all (optional customer filter); customers: own company only.
- `get_project(name)` — single project + linked tickets + comments (access-checked).
- `create_project(...)` / `update_project(name, **fields)` / `delete_project(name)` — agents only.
- `get_project_comments(project)` / `add_project_comment(project, content)` — agents and the project's customer.

`helpdesk/api/addon.py`
- `get_addons(customer=None)` — same scoping as projects.
- `create_addon(...)` / `update_addon(name, **fields)` / `delete_addon(name)` — agents only.

## Frontend

Shared Vue components driven by `isCustomerPortal` (set from `route.meta.public`):

| Component | Routes | Behaviour |
|---|---|---|
| `pages/ProjectsList.vue` | `/projects` (ProjectsAgent), `/my-projects` (ProjectsCustomer) | grid of project cards; agents get a "New project" dialog + customer filter |
| `pages/ProjectView.vue` | `/projects/:id` (ProjectAgent), `/my-projects/:id` (ProjectCustomer) | agents edit/delete inline; customers read-only; both see linked tickets + discussion |
| `pages/AddonsView.vue` | `/addons` (AddonsAgent), `/my-addons` (AddonsCustomer) | grid of add-on cards; agents get create/edit/delete dialog; customers read-only |
| `components/ProjectComments.vue` | — | discussion thread (agent = violet, customer = blue), used in ProjectView |

Sidebar links ("Projects", "Add-ons") are added to both `agentPortalSidebarOptions`
and `customerPortalSidebarOptions` in `components/layouts/layoutSettings.ts`.

## Deploy

New DocTypes + a new ticket field → **migrate required**:

```bash
cd ~/frappe-bench/apps/helpdesk && git pull origin main
cd ~/frappe-bench
bench --site <site> migrate
bench build --app helpdesk
bench --site <site> clear-cache && bench restart
```
