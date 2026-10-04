# Which code is this server process actually running?
#
# Read ONCE, when the module is first imported, from the app's git checkout.
# A web or worker process that wasn't restarted after a deploy keeps
# reporting the commit it started with - which is the point: the desk
# compares it with the commit it was built from, and scripts/deploy.sh asks
# the running server for it, so a half-finished deploy is visible instead of
# being discovered by a user.

import subprocess
from pathlib import Path

import frappe


def _read_commit() -> str:
	repo = Path(__file__).resolve().parents[2]
	try:
		return (
			subprocess.check_output(
				["git", "rev-parse", "--short", "HEAD"],
				cwd=repo,
				stderr=subprocess.DEVNULL,
				timeout=5,
			)
			.decode()
			.strip()
		)
	except Exception:
		return "unknown"


COMMIT = _read_commit()


@frappe.whitelist(allow_guest=True)
def get_build_info() -> dict:
	"""The commit this process loaded. Guest-readable so the deploy script can
	check the live server; the repository is public, so it reveals nothing."""
	return {"commit": COMMIT}
