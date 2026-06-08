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
| `HD Addon Feature` | `feature_title`, `addon` (→ HD Addon), `status` (Planned/In Progress/Released/Deprecated), `project` (→ HD Project, optional), `target_date`, `released_on`, `description` | "upcoming" = Planned/In Progress; tagging `project` surfaces it on that project |
| `HD Addon Task` | `subject`, `addon`, `status` (To Do/In Progress/Done/Blocked), `priority`, `assigned_to` (→ HD Agent), `start_date`, `end_date`, `description` | internal delivery tracking (agent-only) |
| `HD Ticket` | **new** `project` (→ HD Project), `addon` (→ HD Addon) | optional; tags a ticket to a project / add-on |

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
- `get_addon(name)` — single add-on + features + tasks (agents only) + linked tickets + a small dashboard (counts by status).
- `get_features(addon)` / `add_feature(...)` / `update_feature(name, **fields)` / `delete_feature(name)` — read for agents + the add-on's customer; writes agents only. `update_feature` also tags a feature to a project.
- `get_tasks(addon)` / `add_task(...)` / `update_task(name, **fields)` / `delete_task(name)` — agents only.

`helpdesk/api/project.py`
- `get_taggable_features(project)` — add-on features of the project's customer, for the "Tag features" dialog (agents only). `get_project` now also returns `features` (those tagged to the project).

## Add-on detail (features, tasks, dashboard)

`pages/AddonView.vue` (`/addons/:id` agent, `/my-addons/:id` customer) is the
add-on detail page:
- **Header** — agents edit/delete inline; customers read-only.
- **Dashboard** — stat cards: features total + by status, tasks total + by
  status (agents), linked-ticket count.
- **Features** (`components/AddonFeatures.vue`) — agents add/edit-status/delete;
  customers view; "upcoming" features highlighted; shows a project tag if set.
- **Tasks** (`components/AddonTasks.vue`) — agent-only; inline status, priority,
  assignee, start/end dates, with overdue highlighting.
- **Linked tickets** + a **"New ticket"** button (both portals) that opens the
  ticket composer prefilled with `?addon=<name>` (the `new` API persists it).

`ProjectView.vue` gains an **Upcoming features** section listing features tagged
to the project, plus an agent **"Tag features"** dialog (toggles
`HD Addon Feature.project`). `TicketNew.vue` reads `?addon`/`?project` from the
query, shows a context banner, and includes them on the created ticket.

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
