# Copyright (c) 2026, rionatty and contributors
# User acceptance testing (UAT) scripts.
#
# Before go-live, the client's key users prove the system does their work.
# The implementor writes test scripts on a project: numbered steps, each an
# action and the result to expect. Once a script is marked ready, the client
# runs it in the portal and marks every step passed, failed or blocked. A
# failure or a block needs a note saying what happened.
#
# A failed or blocked step becomes a task for the implementor (the "defect"),
# assigned to the script's responsible agent, or else the project lead. When
# that task is marked Done, the step goes back to the client as ready for
# retest. A passed retest closes the task if it is still open.
#
# A script's status follows its steps.

import html

import frappe
from frappe import _
from frappe.utils import cint, format_datetime, get_url, now_datetime, validate_email_address

from helpdesk.api.project import _assert_agent_project, _assert_project_access
from helpdesk.integrations import pumble
from helpdesk.utils import is_agent

OUTCOMES = ("Not run", "Passed", "Failed", "Blocked")
PROBLEMS = ("Failed", "Blocked")
STATUSES = ("Not started", "In progress", "Passed", "Failed", "Blocked")
MAX_STEPS = 200
SCRIPT_FIELDS = [
	"name",
	"title",
	"area",
	"milestone",
	"status",
	"ready_for_testing",
	"tester",
	"responsible_agent",
	"sequence",
	"last_tested_on",
]
STEP_FIELDS = (
	"name",
	"action",
	"expected",
	"outcome",
	"note",
	"tested_by",
	"tested_on",
	"defect_task",
)


# ---------------------------------------------------------------------------
# Pure parts - unit-tested offline
# ---------------------------------------------------------------------------


def script_status(outcomes) -> str:
	"""A script's status from its steps' outcomes. One failure fails the
	script even while other steps are still to run."""
	outcomes = [o or "Not run" for o in outcomes]
	if not outcomes or all(o == "Not run" for o in outcomes):
		return "Not started"
	if "Failed" in outcomes:
		return "Failed"
	if "Blocked" in outcomes:
		return "Blocked"
	if all(o == "Passed" for o in outcomes):
		return "Passed"
	return "In progress"


def step_counts(steps) -> dict:
	"""Counts for a progress bar. `steps` holds (outcome, has_defect) pairs; a
	step not run that has a defect is waiting for a retest."""
	counts = {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "not_run": 0, "retest": 0}
	for outcome, has_defect in steps:
		counts["total"] += 1
		if outcome == "Passed":
			counts["passed"] += 1
		elif outcome == "Failed":
			counts["failed"] += 1
		elif outcome == "Blocked":
			counts["blocked"] += 1
		else:
			counts["not_run"] += 1
			if has_defect:
				counts["retest"] += 1
	return counts


def merge_steps(existing: list, incoming: list) -> list:
	"""The script's steps after an edit, in the new order. A step the editor
	kept (matched by name) keeps its test result; a new step starts "Not
	run"; a step left blank is dropped."""
	by_name = {r["name"]: r for r in existing if r.get("name")}
	out = []
	for row in incoming:
		action = (row.get("action") or "").strip()
		if not action:
			continue
		expected = (row.get("expected") or "").strip() or None
		old = by_name.pop(row.get("name"), None) if row.get("name") else None
		if old:
			out.append({**old, "action": action, "expected": expected})
		else:
			out.append({"action": action, "expected": expected, "outcome": "Not run"})
	return out


def defect_subject(outcome: str, title: str, step_no: int) -> str:
	what = _("UAT failure") if outcome == "Failed" else _("UAT blocker")
	return _("{0}: {1}, step {2}").format(what, title, step_no)[:500]


def defect_description(step_no, action, expected, report_line) -> str:
	return "\n".join(
		[
			_("Step {0}: {1}").format(step_no, action),
			_("Expected: {0}").format(expected or "-"),
			report_line,
		]
	)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def validate_script(doc) -> None:
	"""HD UAT Script.validate - the same rules for the desk form."""
	doc.title = (doc.title or "").strip()
	if not doc.title:
		frappe.throw(_("Give the test script a title"))
	if not doc.steps:
		frappe.throw(_("Add at least one step"))
	if len(doc.steps) > MAX_STEPS:
		frappe.throw(_("A script can have at most {0} steps").format(MAX_STEPS))
	if doc.milestone and frappe.db.get_value("HD Milestone", doc.milestone, "project") != doc.project:
		frappe.throw(_("That milestone belongs to a different project"))
	doc.tester = (doc.tester or "").strip() or None
	if doc.tester:
		validate_email_address(doc.tester, throw=True)
	if doc.responsible_agent and not frappe.db.exists("HD Agent", doc.responsible_agent):
		frappe.throw(_("The responsible person must be an agent"))
	for step in doc.steps:
		if step.outcome not in OUTCOMES:
			step.outcome = "Not run"
	doc.status = script_status([s.outcome for s in doc.steps])


def _project(project: str):
	if not project or not frappe.db.exists("HD Project", project):
		frappe.throw(_("Project not found"), frappe.DoesNotExistError)
	return frappe.get_doc("HD Project", project)


def _names(users) -> dict:
	users = [u for u in set(users) if u]
	if not users:
		return {}
	return {
		u.name: u.full_name or u.name
		for u in frappe.get_all("User", filters={"name": ["in", users]}, fields=["name", "full_name"])
	}


def _defect_states(tasks) -> dict:
	"""Defect task -> "Open" or "Fixed", for the tasks that still exist."""
	tasks = [t for t in set(tasks) if t]
	if not tasks:
		return {}
	return {
		t.name: "Fixed" if t.status == "Done" else "Open"
		for t in frappe.get_all("HD Addon Task", filters={"name": ["in", tasks]}, fields=["name", "status"])
	}


def _payload(doc, agent: bool) -> dict:
	defects = _defect_states(s.defect_task for s in doc.steps)
	names = _names(s.tested_by for s in doc.steps)
	steps = []
	for s in doc.steps:
		outcome = s.outcome or "Not run"
		defect = defects.get(s.defect_task)
		row = {
			"name": s.name,
			"idx": s.idx,
			"action": s.action,
			"expected": s.expected,
			"outcome": outcome,
			"note": s.note,
			"tested_by_name": names.get(s.tested_by, s.tested_by) if s.tested_by else None,
			"tested_on": s.tested_on,
			"defect": defect,
			"retest": bool(defect) and outcome == "Not run",
		}
		if agent:
			row["defect_task"] = s.defect_task if defect else None
		steps.append(row)
	out = {
		f: doc.get(f)
		for f in (
			"name", "project", "title", "area", "milestone", "instructions", "status",
			"ready_for_testing", "tester", "last_tested_on",
		)
	}
	if agent:
		out["responsible_agent"] = doc.responsible_agent
	out["steps"] = steps
	out["counts"] = step_counts((s["outcome"], bool(s["defect"])) for s in steps)
	return out


def _team(doc, project) -> list:
	"""Who hears about this script: the responsible agent, else the lead."""
	for person in (doc.responsible_agent, project.lead):
		if person and frappe.db.get_value("HD Agent", person, "is_active"):
			return [person]
	return []


def _sender():
	return frappe.db.get_value(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")


def _email(recipients, subject, message, doc) -> None:
	"""Sent by a background job after the request commits: the client's click
	never waits on SMTP, and a mail error never reaches the client."""
	recipients = [r for r in recipients if r and r != frappe.session.user]
	if not recipients:
		return
	frappe.enqueue(
		"helpdesk.api.uat.deliver_email",
		queue="short",
		enqueue_after_commit=True,
		recipients=recipients,
		subject=subject,
		message=message,
		script=doc.name,
	)


def deliver_email(recipients, subject, message, script) -> None:
	"""Background job: same sender resolution as the other helpdesk emails."""
	frappe.sendmail(
		recipients=recipients,
		sender=_sender(),
		subject=subject,
		message=message,
		reference_doctype="HD UAT Script",
		reference_name=script,
		now=True,
	)


def notify_defect(task: str) -> None:
	"""Background job: the usual task-assignment email, for a new defect. Not
	sent in the client's request: on a mail error that email tells whoever is
	signed in, with the agent's address."""
	from helpdesk.api.addon import _notify_task_assignee

	if frappe.db.exists("HD Addon Task", task):
		_notify_task_assignee(frappe.get_doc("HD Addon Task", task))


def _raise_defect(doc, step, project) -> None:
	"""A step failed or is blocked: open a task for the implementor, or put
	the report on the step's existing one (reopening it if it was Done)."""
	report = _("{0} on {1} by {2}: {3}").format(
		step.outcome,
		format_datetime(now_datetime(), "d MMM yyyy HH:mm"),
		_names([frappe.session.user]).get(frappe.session.user, frappe.session.user),
		step.note,
	)
	if step.defect_task and frappe.db.exists("HD Addon Task", step.defect_task):
		task = frappe.get_doc("HD Addon Task", step.defect_task)
		task.description = f"{task.description or ''}\n\n{report}".strip()
		if task.status == "Done":
			task.status = "To Do"
			task.completed_on = None
		task.save(ignore_permissions=True)
		return
	from helpdesk.api.addon import _grant_task_access

	team = _team(doc, project)
	task = frappe.get_doc(
		{
			"doctype": "HD Addon Task",
			"project": doc.project,
			"milestone": doc.milestone or None,
			"subject": defect_subject(step.outcome, doc.title, step.idx),
			"status": "To Do",
			"priority": "High",
			"responsibility": "Us",
			"assigned_to": team[0] if team else None,
			"description": defect_description(step.idx, step.action, step.expected, report),
		}
	).insert(ignore_permissions=True)
	step.defect_task = task.name
	_grant_task_access(task)
	if task.assigned_to:
		frappe.enqueue(
			"helpdesk.api.uat.notify_defect",
			queue="short",
			enqueue_after_commit=True,
			task=task.name,
		)


def _close_defect(task_name: str, doc, step) -> None:
	"""The retest passed: close the defect if the team hasn't already."""
	if not task_name or not frappe.db.exists("HD Addon Task", task_name):
		return
	task = frappe.get_doc("HD Addon Task", task_name)
	if task.status == "Done":
		return
	task.status = "Done"
	task.completed_on = now_datetime()
	task.description = (
		f"{task.description or ''}\n\n"
		+ _("Passed the retest on {0}.").format(format_datetime(now_datetime(), "d MMM yyyy HH:mm"))
	).strip()
	task.save(ignore_permissions=True)


def _finished(doc, project) -> None:
	"""Every step has a result: tell the team how the run went."""
	pumble.uat_finished(doc)
	counts = step_counts((s.outcome, False) for s in doc.steps)
	e = html.escape
	link = get_url(f"/helpdesk/projects/{doc.project}")
	if doc.status == "Passed":
		subject = _("UAT passed: {0}").format(doc.title)
		line = _("All {0} steps passed.").format(counts["total"])
	else:
		subject = _("UAT problems: {0}").format(doc.title)
		line = _("{0} passed, {1} failed, {2} blocked, out of {3} steps.").format(
			counts["passed"], counts["failed"], counts["blocked"], counts["total"]
		)
	_email(
		_team(doc, project),
		subject,
		f"<p>{e(_('The client finished testing'))} <b>{e(doc.title)}</b> "
		f"({e(project.project_name or project.name)}).</p><p>{e(line)}</p>"
		f'<p><a href="{e(link)}">{e(_("Open the project"))}</a></p>',
		doc,
	)


def defect_fixed(task: str) -> None:
	"""HD Addon Task.on_update, when a task is marked Done: if it is a UAT
	defect, its step goes back to the client, ready for retest."""
	try:
		parents = set(
			frappe.get_all(
				"HD UAT Step",
				filters={
					"parenttype": "HD UAT Script",
					"defect_task": task,
					"outcome": ["in", list(PROBLEMS)],
				},
				pluck="parent",
			)
		)
	except Exception:
		return  # table may not exist yet (pre-migrate)
	for parent in parents:
		doc = frappe.get_doc("HD UAT Script", parent)
		for step in doc.steps:
			if step.defect_task == task and step.outcome in PROBLEMS:
				step.outcome = "Not run"
		doc.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# API - agents and the project's client
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_scripts(project: str) -> list:
	"""The project's test scripts with their progress. The client sees only
	the ones marked ready for testing."""
	p = _project(project)
	_assert_project_access(p)
	agent = is_agent()
	filters = {"project": project}
	if not agent:
		filters["ready_for_testing"] = 1
	scripts = frappe.get_all(
		"HD UAT Script", filters=filters, fields=SCRIPT_FIELDS, order_by="sequence asc, creation asc"
	)
	if not scripts:
		return []
	steps = frappe.get_all(
		"HD UAT Step",
		filters={"parenttype": "HD UAT Script", "parent": ["in", [s.name for s in scripts]]},
		fields=["parent", "outcome", "defect_task"],
	)
	defects = _defect_states(s.defect_task for s in steps)
	by_script = {}
	for s in steps:
		by_script.setdefault(s.parent, []).append((s.outcome or "Not run", s.defect_task in defects))
	milestones = {
		m.name: m.title
		for m in frappe.get_all(
			"HD Milestone",
			filters={"name": ["in", list({s.milestone for s in scripts if s.milestone}) or [""]]},
			fields=["name", "title"],
		)
	}
	agents = (
		{
			a.name: a.agent_name
			for a in frappe.get_all(
				"HD Agent",
				filters={"name": ["in", list({s.responsible_agent for s in scripts if s.responsible_agent}) or [""]]},
				fields=["name", "agent_name"],
			)
		}
		if agent
		else {}
	)
	for s in scripts:
		s["counts"] = step_counts(by_script.get(s.name, []))
		s["milestone_title"] = milestones.get(s.milestone)
		if agent:
			s["responsible_agent_name"] = agents.get(s.responsible_agent)
		else:
			s.pop("responsible_agent", None)
	return scripts


@frappe.whitelist()
def get_script(name: str) -> dict:
	doc = frappe.get_doc("HD UAT Script", name)
	_assert_project_access(_project(doc.project))
	agent = is_agent()
	if not agent and not doc.ready_for_testing:
		frappe.throw(_("This test script is not open for testing yet"), frappe.PermissionError)
	return _payload(doc, agent)


@frappe.whitelist()
def record_result(script: str, step: str, outcome: str, note: str | None = None) -> dict:
	"""Mark one step passed, failed, blocked, or not run. The client, or an
	agent recording it for them (on a call, say)."""
	doc = frappe.get_doc("HD UAT Script", script)
	project = _project(doc.project)
	_assert_project_access(project)
	agent = is_agent()
	if not agent and not doc.ready_for_testing:
		frappe.throw(_("This test script is not open for testing yet"), frappe.PermissionError)
	if outcome not in OUTCOMES:
		frappe.throw(_("Invalid result"))
	note = (note or "").strip()[:2000] or None
	if outcome in PROBLEMS and not note:
		frappe.throw(_("Say what happened, so the team can put it right"))
	row = next((s for s in doc.steps if s.name == step), None)
	if not row:
		frappe.throw(_("Step not found"), frappe.DoesNotExistError)

	was_complete = all((s.outcome or "Not run") != "Not run" for s in doc.steps)
	row.outcome = outcome
	row.note = note
	if outcome == "Not run":
		row.tested_by = row.tested_on = None
	else:
		row.tested_by = frappe.session.user
		row.tested_on = now_datetime()
		doc.last_tested_on = row.tested_on
		doc.last_tested_by = frappe.session.user
	if outcome in PROBLEMS:
		_raise_defect(doc, row, project)
	doc.save(ignore_permissions=True)

	if outcome in PROBLEMS:
		pumble.uat_problem(doc, row)
	elif outcome == "Passed" and row.defect_task:
		_close_defect(row.defect_task, doc, row)
	complete = all((s.outcome or "Not run") != "Not run" for s in doc.steps)
	if complete and not was_complete:
		_finished(doc, project)
	return _payload(doc, agent)


# ---------------------------------------------------------------------------
# API - agents on the project
# ---------------------------------------------------------------------------


def _email_tester(doc, project) -> None:
	e = html.escape
	link = get_url(f"/helpdesk/my-projects/{doc.project}")
	who = _names([frappe.session.user]).get(frappe.session.user, _("The project team"))
	_email(
		[doc.tester],
		_("Ready for you to test: {0}").format(doc.title),
		f"<p>{e(_('Hello,'))}</p>"
		f"<p>{e(who)} {e(_('has a test script ready for you on'))} "
		f"<b>{e(project.project_name or project.name)}</b>: <b>{e(doc.title)}</b> "
		f"({e(_('{0} steps').format(len(doc.steps)))}).</p>"
		f"<p>{e(_('Open the project, find it under User acceptance testing and click Run. Mark each step passed or failed. If something fails, say what happened and we will put it right.'))}</p>"
		f'<p><a href="{e(link)}">{e(_("Open the project"))}</a></p>',
		doc,
	)


@frappe.whitelist()
def save_script(data) -> dict:
	"""Create or edit a script. With notify_tester, the tester is emailed
	that it is ready (only when it is marked ready for testing)."""
	data = frappe._dict(frappe.parse_json(data) if isinstance(data, str) else (data or {}))
	if data.get("name"):
		doc = frappe.get_doc("HD UAT Script", data.name)
	else:
		doc = frappe.new_doc("HD UAT Script")
		doc.project = data.get("project")
	_assert_agent_project(doc.project)
	for field in ("title", "area", "milestone", "tester", "responsible_agent", "instructions"):
		if field in data:
			value = data.get(field)
			doc.set(field, (value.strip() if isinstance(value, str) else value) or None)
	if "ready_for_testing" in data:
		doc.ready_for_testing = 1 if cint(data.ready_for_testing) else 0
	if "steps" in data:
		existing = [{f: s.get(f) for f in STEP_FIELDS} for s in doc.steps]
		doc.set("steps", [])
		for step in merge_steps(existing, data.get("steps") or []):
			doc.append("steps", step)
	if doc.is_new():
		last = frappe.get_all(
			"HD UAT Script",
			filters={"project": doc.project},
			fields=["sequence"],
			order_by="sequence desc",
			limit_page_length=1,
		)
		doc.sequence = (cint(last[0].sequence) if last else 0) + 1
	doc.save(ignore_permissions=True)
	emailed = None
	if cint(data.get("notify_tester")) and doc.ready_for_testing and doc.tester:
		_email_tester(doc, _project(doc.project))
		emailed = doc.tester
	return {"name": doc.name, "emailed": emailed}


@frappe.whitelist()
def email_tester(name: str) -> str:
	doc = frappe.get_doc("HD UAT Script", name)
	_assert_agent_project(doc.project)
	if not doc.ready_for_testing:
		frappe.throw(_("Mark the script ready for testing first"))
	if not doc.tester:
		frappe.throw(_("Set the tester's email address first"))
	_email_tester(doc, _project(doc.project))
	return doc.tester


@frappe.whitelist()
def reset_steps(name: str, scope: str = "problems") -> dict:
	"""scope "problems": failed and blocked steps go back for a retest (their
	defects stay linked). scope "all": a fresh round, every result cleared."""
	doc = frappe.get_doc("HD UAT Script", name)
	_assert_agent_project(doc.project)
	for step in doc.steps:
		if scope == "all":
			step.outcome = "Not run"
			step.note = step.tested_by = step.tested_on = step.defect_task = None
		elif step.outcome in PROBLEMS:
			step.outcome = "Not run"
	doc.save(ignore_permissions=True)
	return _payload(doc, True)


@frappe.whitelist()
def duplicate_script(name: str) -> str:
	src = frappe.get_doc("HD UAT Script", name)
	_assert_agent_project(src.project)
	return save_script(
		{
			"project": src.project,
			"title": _("{0} (copy)").format(src.title)[:140],
			"area": src.area,
			"milestone": src.milestone,
			"tester": src.tester,
			"responsible_agent": src.responsible_agent,
			"instructions": src.instructions,
			"ready_for_testing": 0,
			"steps": [{"action": s.action, "expected": s.expected} for s in src.steps],
		}
	)["name"]


@frappe.whitelist()
def delete_script(name: str) -> bool:
	project = frappe.db.get_value("HD UAT Script", name, "project")
	if not project:
		frappe.throw(_("Test script not found"), frappe.DoesNotExistError)
	_assert_agent_project(project)
	frappe.delete_doc("HD UAT Script", name, ignore_permissions=True)
	return True
