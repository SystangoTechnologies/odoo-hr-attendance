# On-prem deployment

One Odoo 18 container serving **all four** addon repos on **one port**, which
is how the stack runs on developer machines.

## Why one instance

Odoo cannot be served under a URL sub-path. The web client emits absolute URLs
(`/web/assets/...`, `/odoo/...`, `/websocket`), and `X-Script-Name` is a
Werkzeug convention Odoo's dispatcher does not honour. An earlier version of
this folder tried to front four instances with `/HRattendance`, `/timesheet`,
`/purchaseworkflow` and `/HRexpense`; the first page loaded and every asset
request afterwards missed the proxy routes.

Putting every repo on one `addons_path` gives one port with no routing tricks,
and all 160 modules land in a single Apps list.

If per-product database isolation is ever required, the supported way to keep
one port is nginx virtual hosts on distinct **hostnames**, not paths.

## Layout

| Path | What |
|---|---|
| `docker-compose.yml` | `db` (Postgres 16), `odoo`, `nginx` |
| `Dockerfile` | `odoo:18.0` + `openupgradelib`, `odoo-test-helper` |
| `odoo.conf.template` | rendered to `odoo.conf` by `deploy.sh` |
| `nginx/nginx.conf` | single upstream, websocket upgrade, 200m bodies |
| `clone.sh` | fetches 3 Systango + 15 OCA repos on branch `18.0` |
| `modules.txt` | the 160 modules `deploy.sh` installs |
| `local_addons/` | `web_disable_push` (suppresses the browser push toast) |
| `deploy.sh` | render config → clone → build → init/upgrade → up |
| `Jenkinsfile` | rsync repo to VM, run `deploy.sh`, health check |

`odoo-hr-attendance` is not cloned by `clone.sh` — this folder lives inside
that repo, so its own checkout (`../`) is mounted directly.

## First deploy

```bash
cd /opt/odoo-deploy/deployment
cp .env.example .env
$EDITOR .env            # set both passwords and a free HTTP_PORT
./deploy.sh
```

First run clones ~230 MB of addons and installs 160 modules — expect 15–30
minutes. Afterwards Odoo is on `http://<vm-host>:${HTTP_PORT}/`.

## Later deploys

```bash
./deploy.sh              # sync code + restart, no module work
./deploy.sh --upgrade    # also run `odoo -u` so pulled code takes effect
```

`clone.sh` writes `versions.lock` recording the exact commit of all 19 repos
in the running deploy.

## Requirements

- Docker Engine with the Compose v2 plugin
- ~4 GB RAM, ~20 GB disk
- Outbound HTTPS to github.com (all 19 repos are public — no keys needed)

## Notes

- `ODOO_WORKERS` must be ≥ 1. At 0, Odoo serves websockets in-process on 8069,
  nothing listens on gevent port 8072, and nginx's `/websocket` route 502s.
- Addon mounts are read-only. Python cannot write `__pycache__` into them and
  silently skips it (PEP 3147); this costs a little startup time and nothing else.
- Postgres is not published to the host. Uncomment the `ports:` block in
  `docker-compose.yml` for host-only debugging.
- `admin_passwd` can only be set via the config file — the official Odoo image
  ignores `ADMIN_PASSWORD`/`LIST_DB` environment variables.

## CI/CD

The Jenkinsfile lives only in `odoo-hr-attendance`. `checkout scm` checks out
this repo and rsyncs it to the VM; `clone.sh` then fetches the other three
repos fresh from branch `18.0` on every run. So a change to **any** of the four
repos does reach the VM once the job runs.

What the job does **not** do yet is start itself:

- `triggers { cron(...) }` is commented out.
- Jenkins' "GitHub hook trigger for GITScm polling" only fires for the repo in
  the job's SCM — that is `odoo-hr-attendance` alone. A push to
  `odoo-timesheet`, `odoo-purchase-workflow` or `odoo-hr-expense` will **not**
  start this job until it is wired explicitly.

To trigger from all four, either:

1. **Generic Webhook Trigger plugin** — give the job a token, then add a
   webhook in each of the four GitHub repos pointing at
   `https://<jenkins>/generic-webhook-trigger/invoke?token=<token>`; or
2. **GitHub Actions** — a small workflow in each repo that POSTs to
   `https://<jenkins>/job/<job>/buildWithParameters?token=<token>`.

Either way, add a concurrency guard so two pushes cannot deploy at once.

### Adding a new module

`modules.txt` is the source of truth. A module that is not listed there is
never installed, no matter which repo it lands in — `odoo -u` only upgrades
modules that are already installed. Add the module name to `modules.txt` in
the same change and the next `./deploy.sh --upgrade` will install it.

### Downtime

`--upgrade` stops the `odoo` container, runs `-i`/`-u` over all modules
single-process, then starts it again. nginx stays up and serves 502s during
the window, which for 160 modules is several minutes. Upgrading only the
modules that actually changed would shorten this considerably but is not
implemented.
