# Copyright (c) 2026, rionatty and contributors
# The calendar: every task an agent can see, across projects and add-ons,
# with client sessions told apart - Onsite at the client, or Online - and
# clashes flagged.
#
# A clash is two *sessions* for the same person that overlap. Ordinary tasks
# never clash: a week-long "configure the module" runs alongside other work
# by design. A session with both times set occupies exactly that slot; one
# without times takes its whole day(s). Done and Postponed sessions don't
# occupy anything.
#
# Visibility follows the projects: managers see every task; an agent sees
# the projects and add-ons they are on, plus anything they own, are
# assigned to, or review.

from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import getdate

from helpdesk.utils import is_agent, is_agent_manager

SESSION_TYPES = ("Onsite", "Online")
INACTIVE = {"Done", "Postponed"}
MAX_RANGE_DAYS = 100

# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def as_date(value) -> date | None:
	if not value:
		return None
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value)[:10])


def as_time(value) -> time | None:
	"""A Time field as it comes back from the database (a timedelta), from a
	form ("09:30" / "09:30:00") or already a time."""
	if value in (None, ""):
		return None
	if isinstance(value, time):
		return value
	if isinstance(value, timedelta):
		seconds = int(value.total_seconds()) % 86400
		return time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)
	parts = str(value).split(":")
	return time(
		int(parts[0]),
		int(parts[1]) if len(parts) > 1 else 0,
		int(float(parts[2])) if len(parts) > 2 else 0,
	)


def hhmm(value) -> str | None:
	t = as_time(value)
	return t.strftime("%H:%M") if t else None


def session_window(task) -> tuple | None:
	"""(start, end, timed) as datetimes: the exact slot when both times are
	set, whole days otherwise. None for a task with no date at all."""
	start_d = as_date(task.get("start_date")) or as_date(task.get("end_date"))
	if not start_d:
		return None
	end_d = as_date(task.get("end_date")) or start_d
	if end_d < start_d:
		end_d = start_d
	start_t, end_t = as_time(task.get("start_time")), as_time(task.get("end_time"))
	if start_t and end_t:
		return datetime.combine(start_d, start_t), datetime.combine(end_d, end_t), True
	return (
		datetime.combine(start_d, time.min),
		datetime.combine(end_d + timedelta(days=1), time.min),
		False,
	)


def _occupies(task) -> bool:
	return bool(
		task.get("session_type")
		and task.get("assigned_to")
		and task.get("status") not in INACTIVE
		and session_window(task)
	)


def sessions_clash(a, b) -> bool:
	"""Whether two tasks are the same person's overlapping sessions."""
	if a.get("name") == b.get("name"):
		return False
	if not (_occupies(a) and _occupies(b)):
		return False
	if a.get("assigned_to") != b.get("assigned_to"):
		return False
	wa, wb = session_window(a), session_window(b)
	return wa[0] < wb[1] and wb[0] < wa[1]


def find_clashes(tasks) -> dict:
	"""{task name: sorted names of the sessions it clashes with}."""
	by_person: dict = {}
	for t in tasks:
		if _occupies(t):
			by_person.setdefault(t["assigned_to"], []).append(t)
	out: dict = {}
	for items in by_person.values():
		items.sort(key=lambda t: session_window(t)[0])
		for i, a in enumerate(items):
			wa = session_window(a)
			for b in items[i + 1 :]:
				wb = session_window(b)
				if wb[0] >= wa[1]:
					break  # sorted by start: nothing later reaches back into `a`
				out.setdefault(a["name"], set()).add(b["name"])
				out.setdefault(b["name"], set()).add(a["name"])
	return {name: sorted(names) for name, names in out.items()}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

TASK_COLUMNS = (
	"name",
	"subject",
	"status",
	"priority",
	"project",
	"addon",
	"owner",
	"assigned_to",
	"reviewer",
	"start_date",
	"end_date",
	"session_type",
	"start_time",
	"end_time",
	"location",
	"meeting_link",
)


def _assert_agent() -> None:
	if not is_agent():
		frappe.throw(_("Only agents can use the calendar"), frappe.PermissionError)


def _memberships(user: str) -> tuple:
	"""(projects, add-ons) the user is on."""
	projects = set(
		frappe.get_all("HD Project Member", filters={"agent": user}, pluck="project")
	)
	projects |= set(frappe.get_all("HD Project", filters={"lead": user}, pluck="name"))
	addons = set(
		frappe.get_all("HD Addon Member", filters={"agent": user}, pluck="addon")
	)
	return projects, addons


def _tasks_between(start_d: date, end_d: date, assigned_to: str | None = None) -> list:
	"""Tasks with any day inside [start_d, end_d] the caller may see."""
	from frappe.query_builder.functions import Coalesce

	T = frappe.qb.DocType("HD Addon Task")
	first = Coalesce(T.start_date, T.end_date)
	last = Coalesce(T.end_date, T.start_date)
	q = (
		frappe.qb.from_(T)
		.select(*[T[c] for c in TASK_COLUMNS])
		.where(first.isnotnull())
		.where(first <= end_d)
		.where(last >= start_d)
	)
	if assigned_to:
		q = q.where(T.assigned_to == assigned_to)
	user = frappe.session.user
	if not is_agent_manager(user):
		projects, addons = _memberships(user)
		allowed = (T.assigned_to == user) | (T.owner == user) | (T.reviewer == user)
		if projects:
			allowed = allowed | T.project.isin(sorted(projects))
		if addons:
			allowed = allowed | T.addon.isin(sorted(addons))
		q = q.where(allowed)
	return q.run(as_dict=True)


def _can_open(task, user: str, projects: set, addons: set) -> bool:
	return bool(
		is_agent_manager(user)
		or user in (task.get("assigned_to"), task.get("owner"), task.get("reviewer"))
		or (task.get("project") and task.get("project") in projects)
		or (task.get("addon") and task.get("addon") in addons)
	)


def _enrich(rows: list) -> None:
	"""Names for the people and parents, and times as HH:MM."""
	projects = {r.project for r in rows if r.get("project")}
	addons = {r.addon for r in rows if r.get("addon")}
	agents = {r.assigned_to for r in rows if r.get("assigned_to")}
	project_rows = (
		{
			p.name: p
			for p in frappe.get_all(
				"HD Project",
				filters={"name": ["in", sorted(projects)]},
				fields=["name", "project_name", "customer"],
			)
		}
		if projects
		else {}
	)
	addon_rows = (
		{
			a.name: a
			for a in frappe.get_all(
				"HD Addon",
				filters={"name": ["in", sorted(addons)]},
				fields=["name", "addon_name", "customer"],
			)
		}
		if addons
		else {}
	)
	agent_names = (
		{
			a.name: a.agent_name
			for a in frappe.get_all(
				"HD Agent",
				filters={"name": ["in", sorted(agents)]},
				fields=["name", "agent_name"],
			)
		}
		if agents
		else {}
	)
	for r in rows:
		parent = project_rows.get(r.get("project")) or addon_rows.get(r.get("addon"))
		r["parent_label"] = (
			(parent.get("project_name") or parent.get("addon_name")) if parent else None
		)
		r["customer"] = parent.get("customer") if parent else None
		r["assigned_to_name"] = agent_names.get(r.get("assigned_to")) or r.get("assigned_to")
		r["start_time"] = hhmm(r.get("start_time"))
		r["end_time"] = hhmm(r.get("end_time"))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_events(
	start: str,
	end: str,
	agent: str | None = None,
	session_type: str | None = None,
) -> list:
	"""Tasks between `start` and `end` (inclusive dates) for the calendar.
	`agent` narrows to one person ("@me" for the caller); `session_type` to
	"Onsite", "Online" or "Task" (ordinary tasks). Clashes are worked out
	before the narrowing, so an onsite session that clashes with an online
	one is still flagged when only onsite sessions are shown."""
	_assert_agent()
	start_d, end_d = getdate(start), getdate(end)
	if end_d < start_d:
		start_d, end_d = end_d, start_d
	if (end_d - start_d).days > MAX_RANGE_DAYS:
		frappe.throw(_("Pick a range of at most {0} days").format(MAX_RANGE_DAYS))

	rows = _tasks_between(start_d, end_d)
	clashes = find_clashes(rows)

	if agent == "@me":
		agent = frappe.session.user
	if agent:
		rows = [r for r in rows if r.get("assigned_to") == agent]
	if session_type in SESSION_TYPES:
		rows = [r for r in rows if r.get("session_type") == session_type]
	elif session_type == "Task":
		rows = [r for r in rows if not r.get("session_type")]

	_enrich(rows)
	for r in rows:
		r["clashes_with"] = clashes.get(r.name, [])
		for private in ("owner", "reviewer"):
			r.pop(private, None)
	return rows


@frappe.whitelist()
def get_clashes(task: str) -> dict:
	"""The sessions that clash with this one, for the task drawer's warning.
	Ones the caller can't open are counted, not named."""
	_assert_agent()
	row = frappe.db.get_value("HD Addon Task", task, list(TASK_COLUMNS), as_dict=True)
	if not row or not _occupies(row):
		return {"clashes": [], "hidden": 0}
	window = session_window(row)
	first_day = window[0].date()
	last_day = (window[1] - timedelta(seconds=1)).date()

	# Every session of the assignee in those days, whoever can see them.
	from frappe.query_builder.functions import Coalesce

	T = frappe.qb.DocType("HD Addon Task")
	first = Coalesce(T.start_date, T.end_date)
	last = Coalesce(T.end_date, T.start_date)
	others = (
		frappe.qb.from_(T)
		.select(*[T[c] for c in TASK_COLUMNS])
		.where(T.assigned_to == row.assigned_to)
		.where(T.name != row.name)
		.where(first.isnotnull())
		.where(first <= last_day)
		.where(last >= first_day)
		.run(as_dict=True)
	)
	clashing = [o for o in others if sessions_clash(row, o)]

	user = frappe.session.user
	projects, addons = _memberships(user)
	visible = [o for o in clashing if _can_open(o, user, projects, addons)]
	_enrich(visible)
	for o in visible:
		for private in ("owner", "reviewer"):
			o.pop(private, None)
	return {"clashes": visible, "hidden": len(clashing) - len(visible)}
