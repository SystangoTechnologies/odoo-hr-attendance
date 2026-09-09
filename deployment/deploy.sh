#!/usr/bin/env bash
# One-shot deploy. Assumes CI has already synced this repo (module code +
# deployment/) onto the VM.
#
#   ./deploy.sh              sync addon repos, build, start. Initialises the
#                            database and installs modules on first run only.
#   ./deploy.sh --upgrade    same, then run `odoo -u` over modules.txt so
#                            freshly pulled code takes effect.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

UPGRADE=0
[ "${1:-}" = "--upgrade" ] && UPGRADE=1

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill it in." >&2
  exit 1
fi

# Read .env the way Compose does, NOT by sourcing it. A .env file is not a
# shell script: sourcing a password containing | & ; ` or $( ) would break
# this script or execute part of the password.
read_env() {
  sed -n "s/^[[:space:]]*$1[[:space:]]*=//p" .env | tail -n1 \
    | sed -e "s/^'\(.*\)'$/\1/" -e 's/^"\(.*\)"$/\1/'
}

POSTGRES_USER="$(read_env POSTGRES_USER)"
POSTGRES_PASSWORD="$(read_env POSTGRES_PASSWORD)"
ODOO_ADMIN_PASSWORD="$(read_env ODOO_ADMIN_PASSWORD)"
DB_NAME="$(read_env ODOO_DB_NAME)";  DB_NAME="${DB_NAME:-odoo}"
WORKERS="$(read_env ODOO_WORKERS)";  WORKERS="${WORKERS:-2}"
HTTP_PORT="$(read_env HTTP_PORT)";   HTTP_PORT="${HTTP_PORT:-8092}"

: "${POSTGRES_USER:?set in .env}"
: "${POSTGRES_PASSWORD:?set in .env}"
: "${ODOO_ADMIN_PASSWORD:?set in .env}"

if [ "$WORKERS" -lt 1 ]; then
  echo "ERROR: ODOO_WORKERS must be >= 1. At 0 nothing listens on the gevent" >&2
  echo "       port and nginx's /websocket route breaks." >&2
  exit 1
fi

# --- render odoo.conf ------------------------------------------------------
# Substitution is done with awk index/substr, deliberately NOT with sed or
# bash ${x//a/b}: both treat a bare & in the replacement as the matched text
# (bash since 5.2), which silently mangles any password containing &.
# Values are passed through ENVIRON so awk does not process backslash escapes.
export ODOO_ADMIN_PASSWORD POSTGRES_USER POSTGRES_PASSWORD DB_NAME WORKERS
( umask 077
  awk '
  function rep(s, k, v,   i, out) {
    while ((i = index(s, k)) > 0) {
      out = out substr(s, 1, i - 1) v
      s = substr(s, i + length(k))
    }
    return out s
  }
  {
    $0 = rep($0, "__ADMIN_PASSWORD__", ENVIRON["ODOO_ADMIN_PASSWORD"])
    $0 = rep($0, "__DB_USER__",        ENVIRON["POSTGRES_USER"])
    $0 = rep($0, "__DB_PASSWORD__",    ENVIRON["POSTGRES_PASSWORD"])
    $0 = rep($0, "__DB_NAME__",        ENVIRON["DB_NAME"])
    $0 = rep($0, "__WORKERS__",        ENVIRON["WORKERS"])
    print
  }' odoo.conf.template > odoo.conf
)
chmod 600 odoo.conf

# --- addon repos -----------------------------------------------------------
./clone.sh

# --- build & database ------------------------------------------------------
docker compose pull db nginx
docker compose build odoo
docker compose up -d db

echo "Waiting for Postgres..."
for _ in $(seq 1 60); do
  if docker compose exec -T db pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; then break; fi
  sleep 2
done

db_exists() {
  docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1
}

# Strip comments/blanks and join into the comma-separated list Odoo expects.
MODULES="$(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' modules.txt | tr -d '[:space:]' | paste -sd, -)"
MODULE_COUNT="$(printf '%s' "$MODULES" | tr ',' '\n' | wc -l)"

# A schema migration must not run while the live instance is serving: two Odoo
# processes on one database race the registry and deadlock on the same rows.
# Stop odoo first. nginx stays up so users get a 502 rather than a refused
# connection. Always single-process -- with workers > 0 the forked children
# race the migration too.
odoo_oneshot() {
  docker compose stop odoo >/dev/null 2>&1 || true
  docker compose run --rm --no-TTY odoo \
    odoo -c /etc/odoo/odoo.conf -d "$DB_NAME" "$@" \
    --workers=0 --max-cron-threads=0 --stop-after-init
}

if ! db_exists; then
  echo "Database '$DB_NAME' not found -- initialising and installing $MODULE_COUNT modules."
  echo "First run also clones ~230 MB of addons; expect 15-30 minutes."
  odoo_oneshot -i "$MODULES" --without-demo=all
elif [ "$UPGRADE" = "1" ]; then
  echo "Upgrading $MODULE_COUNT modules in '$DB_NAME'..."
  # -i alongside -u: entries newly added to modules.txt get installed,
  # already-installed ones get upgraded. Each flag is a no-op for the other case.
  odoo_oneshot -i "$MODULES" -u "$MODULES"
else
  echo "Database '$DB_NAME' exists -- skipping module install."
  echo "Run './deploy.sh --upgrade' to apply pulled code changes."
fi

# --- start -----------------------------------------------------------------
docker compose up -d

echo
echo "Deployed. Odoo is on http://<vm-host>:${HTTP_PORT}/"
echo "All four repos' modules are in this one instance and one Apps list."
