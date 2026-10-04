#!/usr/bin/env bash
# One-command deploy for this helpdesk. On the server:
#
#   ~/frappe-bench/apps/helpdesk/scripts/deploy.sh [site]
#
# Pulls, migrates, builds, restarts web + workers through supervisor, then
# asks the RUNNING server which commit it is serving - so a half-finished
# deploy (say, a restart that died on the node-socketio error) is reported
# here instead of being discovered by a user.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_DIR="$(cd "$APP_DIR/../.." && pwd)"
BENCH_NAME="$(basename "$BENCH_DIR")"
SITE="${1:-$(cat "$BENCH_DIR/sites/currentsite.txt" 2>/dev/null || true)}"
if [ -z "$SITE" ]; then
	echo "usage: $0 <site>   (no default site is set)" >&2
	exit 1
fi

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

cd "$APP_DIR"
step "Pulling"
BEFORE="$(git rev-parse --short HEAD)"
git pull --ff-only
AFTER="$(git rev-parse --short HEAD)"
if [ "$BEFORE" = "$AFTER" ]; then
	echo "Already at $AFTER - finishing the deploy anyway, in case an earlier one stopped halfway."
else
	echo "$BEFORE -> $AFTER"
	git --no-pager log --oneline "$BEFORE..$AFTER" | head -25
fi

cd "$BENCH_DIR"
step "Migrating $SITE"
bench --site "$SITE" migrate

step "Building the desk app"
bench build --app helpdesk

step "Restarting web + workers"
# Not `bench restart`: on this server it can abort on the node-socketio spawn
# error before it reaches the workers, leaving them on the old code.
sudo supervisorctl restart "${BENCH_NAME}-web:" "${BENCH_NAME}-workers:" ||
	echo "supervisorctl reported a problem - status below"
sudo supervisorctl status | grep -E "^${BENCH_NAME}-" || true

step "Clearing cache"
bench --site "$SITE" clear-cache

step "Checking what the running server serves"
PORT="$(python3 -c "import json; print(json.load(open('sites/common_site_config.json')).get('webserver_port', 8000))" 2>/dev/null || echo 8000)"
SERVED=""
for _ in $(seq 1 10); do
	SERVED="$(curl -s -H "Host: $SITE" "http://127.0.0.1:$PORT/api/method/helpdesk.api.version.get_build_info" |
		python3 -c "import sys, json; print(json.load(sys.stdin)['message']['commit'])" 2>/dev/null || true)"
	[ -n "$SERVED" ] && break
	sleep 3
done

if [ "$SERVED" = "$AFTER" ]; then
	printf '\n\033[1;32mDeployed %s - the server is running it.\033[0m\n' "$AFTER"
else
	printf '\n\033[1;31mThe server reports "%s", expected %s. The restart did not take - check the supervisor status above.\033[0m\n' "${SERVED:-no answer}" "$AFTER"
	exit 1
fi
