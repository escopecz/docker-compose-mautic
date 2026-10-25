# Self-host Mautic 7 with Docker Compose

A working example for running multiple Mautic instances on one server. It uses Mautic **7.2.1** with PHP **8.3.36** and a shared MySQL **8.4** service. Each instance gets its own database user, schema, internal database network, configuration and media volumes. All instances share one application image.

The sample names `marketing` and `sales` and all `example.com` domains are placeholders. There are no production hostnames, SSH keys, provider tokens or automatic deployments. CI validates the example; pushing or merging changes never connects to a server.

## Install

Use a Linux server with Docker Engine, Docker Compose v2, Python 3.11+ and a host reverse proxy such as nginx. The pinned Mautic image is amd64; ARM machines need emulation. Start with at least 4 GB RAM for two instances and the image build, then size for your workload. Build on a separate machine and transfer the image if the server has limited RAM.

```sh
cp instances.example.json instances.json
# Edit the names, domains and unused loopback ports before proceeding.
python3 scripts/render.py --init-secrets
# Build once, including the GrapesJS editor assets absent from the upstream image.
docker build --platform linux/amd64 -t mautic-example:7.2.1 .
docker compose -f compose.json up -d
```

Generated passwords stay in ignored, owner-only `secrets/` files. Save them securely with your backups. Running the renderer again does not rotate passwords. MySQL creates the users only on its first startup with an empty volume. Adding/renaming instances later requires deliberate database/user provisioning; do not delete the database volume to rerun initialization.

Only web services start by default. Each listens on `127.0.0.1`; MySQL has no published port. Complete the installation wizard through an SSH tunnel **before exposing a hostname publicly**:

```sh
ssh -L 8001:127.0.0.1:8001 -L 8002:127.0.0.1:8002 user@your-server
```

Open `http://localhost:8001` and `http://localhost:8002`, create each administrator, then configure your real HTTPS site URL. Email initially uses a null transport; configure and test your own SMTP provider in Mautic before enabling campaigns or jobs.

## HTTPS and jobs

Adapt `nginx.example.conf` for each hostname and obtain certificates with your ACME client. The example overwrites forwarded headers instead of trusting values supplied by visitors. For HTTPS detection behind nginx, set `trusted_proxies` in the instance's persisted `config/local.php` to the exact Docker bridge gateway address through which nginx reaches that web container. For a fresh installation you can set the same addresses in `instances.json` before startup. Inspect them using `docker network inspect`; do not trust all IPs or use `REMOTE_ADDR`.

Reload nginx only after its configuration passes `nginx -t`. Point your DNS to your own server. Keep Docker backend ports bound to loopback. Restrict SSH and host firewall access appropriately. Logs can still contain personal data and error details; restrict and rotate them, and never publish them as CI artifacts.

After installation and SMTP validation, enable the instance's cron and queue consumer explicitly:

```sh
docker compose -f compose.json --profile jobs up -d marketing-cron marketing-worker
# Repeat for sales when ready.
```

The official image's cron schedule and queue worker are used. If an external scheduler already runs these commands, leave local cron disabled to avoid duplicate jobs. Keep the worker enabled when using Doctrine queues unless another consumer handles them.

## Backups and restore rehearsal

```sh
python3 scripts/backup.py backup marketing
python3 scripts/backup.py rehearse marketing --directory backups/marketing/TIMESTAMP
```

Backup briefly stops only that instance's running web/cron/worker services, dumps its schema, archives its configuration/media, checks archive integrity and restarts the same services. Schedule this command using your host's scheduler. Backups are private, unencrypted files: retain an encrypted off-server copy and manage retention according to your policy. They contain database credentials and customer data.

Rehearsal checks the manifest, restores SQL into a disposable MySQL container with **no network access**, and verifies the scheduler is **DISABLED** before importing. MySQL local shell commands and local file loading are disabled during imports. No web, email, cron or queue worker runs; the scratch container and its anonymous volume are removed afterwards. This proves database restoreability, not application compatibility or a complete disaster recovery test. Test application restoration separately before relying on a recovery plan.

There is intentionally no automatic production restore. For recovery, stop the selected instance's writers, preserve its current data, verify a backup, restore the configuration/media and import SQL with the supplied binary-mode client into a clean matching schema. Never restore over live writes. Keep the exact application image identified in the manifest and the secret files alongside your recovery material.

## Updates and migrations

Application startup does **not** run database migrations. Back up and rehearse first, build a reviewed new image, stop the selected instance's writers and run the version-appropriate Mautic migration commands explicitly before reopening traffic. Runtime images are pinned; periodically review upstream security releases and update the pins. Do not assume an old digest gets security fixes automatically.

Do not mount a persistent volume over all of `/var/www/html`: it would hide updated application code. Custom plugins/themes belong in a reviewed derived image. Persistent configuration/media/logs are shared only between the roles of the same instance.

This is a fresh Mautic 7 hosting example, not an unattended Mautic 4/5/6 upgrader. Existing installations must follow the supported major-version migration path and validate their plugins, themes, schema and data before cutover. Avoid `docker compose down -v` on live installations: it deletes persistent data for every instance in that project.

## Validation

```sh
python3 -m unittest discover -s tests -v
docker compose -f compose.json --profile jobs config --quiet
python3 tests/integration.py
```

The integration test creates only disposable test resources with random names and dummy credentials. It checks per-schema access (including GRANT wildcard protection), blocked MySQL shell commands, disabled database events, secret-free process arguments, installation, editor assets, background jobs and a database backup/restore cycle. It does not read your instance secrets or connect to an existing server.
