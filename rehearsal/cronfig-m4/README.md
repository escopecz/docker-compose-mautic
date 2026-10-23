# Private Cronfig M4 restore configuration

These are configuration templates only. The application, local.php, SQL dumps and checkpoints are private and outside this repository. Do not start an empty project here and mistake it for the restored application.

Based on the upstream Mautic 4.4.8 `.ddev/config.yaml`, adapted to PHP 8.0 / MySQL 8.0 to match the source. Upstream post-start installation hooks are deliberately omitted: this is an existing installation. The package-key refresh follows https://packages.sury.org/php/README.txt and retains package signature verification.

The working copy uses the unique database host `ddev-cronfig-migration-m4-db`, database/user/password `db`, local site URL `http://127.0.0.1:8184`, SMTP `127.0.0.1:1025`, no SMTP credentials and no encryption. These overrides are appended to its private local.php. Preserve original encryption keys and table prefix, but never use production database/mail connections locally. Do not start cron or queue consumers. MySQL scheduled events are disabled.

DDEV 1.24.8 adds its shared network even when Compose network overrides request isolation. The custom web initialization script is therefore essential: it applies IPv4/IPv6 OUTPUT DROP, allows loopback, reply traffic and only this project's database on port 3306. It runs before supervisord starts PHP/Apache and fails startup if firewall setup fails. NET_ADMIN is needed for this local firewall; this is not a production container capability recommendation. DDEV's normal trusted developer root access can alter these rules, so this is an accidental-outbound guard, not a hostile-code sandbox.

Before every import or upgrade, verify the firewall is present, an external TCP connection times out, the unique database hostname points to the expected empty/restored schema, and MySQL event_scheduler is OFF. Do not use the generic hostname `db`: other DDEV projects may also advertise it. Recheck after restart; database IPs can change.

The existing global DDEV router is unhealthy on this Mac. DDEV may return failure while waiting for that unrelated router after both project containers become healthy. Use the explicit loopback port, and check the project's actual health independently. Do not change other projects or global router settings as part of this migration.

Initial local checks on 2026-10-23:
- Mautic 4.4.8 CLI and PHP 8.0.30 verified.
- 118 tables, 69,463 contacts, 99,156 form submissions, 69,302 email-stat records.
- Login and form generation for forms 1 and 9 return HTTP 200.
- Asset 1 redirects to the configured Cronfig plugin GitHub archive (HTTP 302).
- Outbound TCP connection blocked; local database connection succeeds.
- After restart, firewall rules remain present and MySQL event scheduler stays OFF.
- A private M4 database checkpoint, configuration copy and verification record are saved outside Git. Original source archive remains untouched.

These checks do not prove plugin compatibility with later Mautic versions. Browser form submissions, email content and background-task behavior require isolated functional tests at each upgrade checkpoint. Browser-side absolute URLs must be audited before interacting with previews.

Run one rehearsal database stage at a time on this Mac: Docker currently has approximately 3.8 GiB RAM shared with other projects. Running M4 and M5 concurrently exhausted that allocation during an import. The M4 containers were stopped after checkpoint creation; the M5 import was restarted into an empty local schema. The rehearsal MySQL configuration limits its buffer pool to 64 MiB, disables performance_schema and caps connections at 30. These are local migration settings, not production sizing recommendations.
