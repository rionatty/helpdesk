# Project Management — Target Design

Status: **DRAFT for review** · Builds on `projects-and-addons.md` (current state).

## Vision

One support desk that runs the whole delivery lifecycle:

- **Customer projects** — client engagements with milestones, visible progress, and a client-facing status page.
- **Internal projects** — same machinery, never shown on the portal (infrastructure, R&D, housekeeping).
- **Tickets** — customer-reported issues that can be converted into internal tasks with a backlink.
- **Add-on development** — features scoped per add-on, delivered through project milestones, with tasks attached to each feature.
- **Agent workload** — every agent has a "My tasks" view across all projects/add-ons; managers see workload distribution.

## Gap analysis (what's missing today)

| # | Gap | Why it matters |
|---|-----|----------------|
| 1 | `HD Project.customer` is required | No internal projects possible |
| 2 | No milestones | No phases, no rollup, no client-facing plan |
| 3 | Tasks can't attach to a feature or milestone | "Tasks per feature/milestone" is the user's core ask |
| 4 | No ticket → task conversion | Customer bug reports die in the ticket queue |
| 5 | `progress` is a manually typed Int | Goes stale; should roll up from tasks |
| 6 | No "My tasks" page | Agents have no personal worklist |
| 7 | No time tracking on tasks | Can't estimate or bill effort |
| 8 | No checklists/subtasks inside a task | Tasks are atomic only |
| 9 | No notifications | Assignment/overdue/milestone events are silent |
| 10 | No activity feed | No audit trail of who changed what |
| 11 | No attachments on tasks/projects | Specs and screenshots live elsewhere |
| 12 | No drag-and-drop on the kanban | Status changes need the dialog |
| 13 | No timeline/Gantt view | No visual plan against dates |
| 14 | No project templates | Every add-on project rebuilt by hand |
| 15 | No workload/overdue reporting | Managers fly blind |

## Data model changes

### HD Project (modify)
- `project_type` Select: **Customer / Internal** (default Customer).
- `customer` becomes required **only when** `project_type = Customer` (`mandatory_depends_on`). Internal projects never appear on the portal.
- `priority` Select: Low/Medium/High.
- `lead` Link → HD Agent (project owner, distinct from team).
- `progress` becomes **computed** (weighted % of Done tasks) with an `auto_progress` toggle so manual override stays possible.

### HD Milestone (new)
- `project` Link → HD Project (reqd), `title`, `description`.
- `status` Select: Upcoming / In Progress / Completed / Missed.
- `due_date` Date, `sequence` Int (ordering), `completed_on` Date.
- `customer_visible` Check (default 1; internal milestones hidden from portal).
- Progress computed from its tasks.

### HD Addon Task → becomes the universal task (modify; keep doctype name for migration safety)
- New optional links: `milestone` → HD Milestone, `feature` → HD Addon Feature, `ticket` → HD Ticket (origin).
- Parent rule: at least one of `addon` / `project` (as today); `milestone`/`feature` refine placement within them.
- `estimate_hours` Float, `is_internal` Check (hide a specific task from the customer even on a customer project).
- `depends_on` Link → HD Addon Task (simple blocked-by; a blocked task with an open dependency shows a chain badge).
- Child table `checklist` → **HD Task Checklist Item** (new): `item` Data, `done` Check.

### HD Task Time Log (new)
- `task` Link (reqd), `agent` Link → HD Agent, `hours` Float, `date` Date, `note` Data.
- Rolls up to `actual_hours` on the task; estimate vs actual shown on task and project.

### HD Addon Feature (modify)
- `milestone` Link → HD Milestone ("delivered in").

### HD Project Template + HD Project Template Row (new, phase 4)
- Named template (e.g. "Add-on development") with rows defining milestones and default tasks (subject, offset days, default assignee role). "New project from template" stamps out the structure.

### HD Pumble Settings (new, single doctype)
- `enabled` Check, `api_key` Password, `workspace_id` Data.
- `default_webhook_url` Data (fallback channel for events with no routing).
- `notify_new_ticket`, `notify_task_assigned`, `notify_task_done`, `notify_milestone_completed`, `notify_customer_comment` Checks — global event toggles.

### Pumble routing fields (modify)
- `HD Project.pumble_webhook_url` Data — project events go to this channel.
- `HD Team.pumble_webhook_url` Data — team-level fallback.
- `HD Agent.pumble_member_id` Data — for @mentions in messages.

## Behaviour

### Ticket ↔ task
- "Convert to task" action on a ticket (agent only): creates a task with `ticket` set, subject/description copied, parent project/add-on prefilled from the ticket's links.
- Task detail shows the origin ticket; ticket detail shows linked tasks with status.
- When the linked task is set to Done, prompt the agent to update/reply to the ticket (no silent auto-close).

### Progress rollup
- Task status change → recompute milestone progress → recompute project progress (`auto_progress` projects only). Weight = `estimate_hours` if set, else 1.

### Notifications (Frappe email + in-app)
- Task assigned → notify assignee.
- Daily digest per agent: overdue + due-today tasks.
- Milestone completed on a customer project → optional customer email (toggle per project).
- @mention in a comment → notify the mentioned user.

### Pumble integration (outbound chat notifications)

Pumble offers two mechanisms, both on the free plan; we use both:

- **Incoming webhooks** (primary) — one webhook URL per Pumble channel; we POST `{"text": ...}` to it. Zero-config per event, just paste the channel's webhook URL on the project/team. Rate limit one message per second per webhook, 10k chars max.
- **API key addon** (secondary, optional) — `sendMessage`, `sendReply`, `addReaction`, `createChannel`, `listChannels` via the Pumble API. Unlocks "create a Pumble channel automatically for each new project" and threaded follow-ups. Configured once in HD Pumble Settings.

**Routing** — most specific channel wins: task/milestone events → its project's webhook → owning team's webhook → default webhook. Ticket events → default (support) webhook.

**Events** (each toggleable in HD Pumble Settings):

| Event | Message | Channel |
|-------|---------|---------|
| New ticket | subject, customer, priority + portal link | support default |
| Task assigned | subject, due date, @mention assignee | project channel |
| Task done / blocked | subject, who, milestone | project channel |
| Milestone completed | milestone, project, progress % | project channel |
| Customer commented | excerpt + link (project or task thread) | project channel |
| Daily digest | per-agent overdue/due-today rollup | team channel |

**Delivery** — a thin `helpdesk/integrations/pumble.py` adapter; every send goes through `frappe.enqueue` (background queue) with retry, so a Pumble outage can never block or slow a save. Failures log to Error Log, never to the user.

**Inbound (exploratory, not committed)** — creating tickets/tasks from Pumble messages would need Pumble's app platform/slash commands; park until the outbound flow proves itself.

### Activity feed
- Enable `track_changes` on HD Project, HD Milestone, HD Addon Task.
- `get_activity(project)` merges: comments, task create/status changes, milestone changes, ticket links — one chronological feed on ProjectView.

### Attachments
- Use Frappe's native File attachments on HD Project and HD Addon Task; surface upload/list in the task dialog and project sidebar. Customer-visible on customer projects unless the task is `is_internal`.

## Views

| View | Audience | Content |
|------|----------|---------|
| Kanban (exists, upgrade) | Agents | Drag-and-drop between columns; filter by milestone/feature/assignee; group-by toggle (status / milestone / assignee) |
| **My tasks** (new) | Agents | All my tasks across everything, grouped Overdue / Today / This week / Later; inline status toggle; time-log quick entry |
| **Timeline** (new) | Agents | Milestones as rows on a date axis, task bars inside; light CSS Gantt (no dependencies rendering in v1) |
| **Client status page** (new) | Customers | Per customer project: milestone tracker (done/current/upcoming), visible tasks, progress %, features, linked tickets, comment thread — replaces the raw ProjectView for the portal |
| **Workload dashboard** (new) | Agent managers | Open/overdue tasks per agent, estimate vs actual hours, unassigned queue |

## Access model (unchanged philosophy, two additions)

- Agents manage everything; customers see only their company's records via whitelisted APIs with explicit checks (current pattern).
- **Internal projects and `is_internal` tasks are never returned to portal sessions** — filtered in the API layer, not just hidden in the UI.
- Customer-facing payloads strip agent emails (`owner`, `assigned_to`) and return display names only.

## Delivery phases

1. **Foundations** — internal projects (`project_type`), HD Milestone, task links (milestone/feature/ticket), migration. The model is right before anything is built on it. **✅ Shipped** (also includes: priority + lead on projects, `is_internal` tasks, milestone tracker UI on ProjectView, milestone/feature pickers + milestone filter on the task board, agent emails stripped from all portal payloads).
2. **Daily drivers** — My tasks page, ticket → task conversion, drag-and-drop kanban, checklists, progress rollups.
3. **Communication** — notifications + daily digest, **Pumble integration (webhooks first, API addon second)**, activity feed, attachments, client status page.
4. **Scale** — time logs + estimate vs actual, timeline view, project templates, workload dashboard.

Each phase ships independently behind a `bench migrate`.
