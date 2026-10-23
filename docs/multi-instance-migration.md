# Multi-instance preparation and migration

Status: preparation only. No production deployment command is implemented. No files, credentials or database contents from the servers belong in this repository. The existing Veetr application and database have not been moved into the proposed layout.

## Repository and runtime ownership

Use one maintained branch with one reviewed manifest per instance. Each manifest can pin its own application version, image and required plugins. Empty plugin lists mean inventory pending, not confirmation that no plugins exist. The current image is the base Mautic image; it does not prove custom plugins have been packaged or tested.

Use a GitHub Environment for each instance's future deployment secrets. Pushes/PRs should validate, never upgrade every instance. A future manual deployment selects one allowlisted instance and a tested immutable release. Take an instance lock and a host-wide migration lock; do not run simultaneous memory-heavy upgrades on this host.

Keep MySQL 8.4 in a separate Docker Compose project, with its own persistent external volume, root credential and backup lifecycle. Application projects cannot own or replace that service or its storage. This retains reproducible database versions without installing MySQL packages directly on the host. Docker is not a separate guest OS; running one MySQL container avoids the duplicated database processes of three independent stacks. All instances share the database server's failure/resource limits, but use distinct schemas and restricted users.

Create a separate internal Docker database network per application, with the shared MySQL service connected to all three. No host port is published for MySQL. Give each application outbound connectivity separately. Never grant application users access to another instance's schema or global administrative permissions. Server credentials live under `/etc/mautic` with root-only permissions; the database root secret is not provided to application containers.

Candidate Compose files can be rendered without reading credentials or contacting a server:

```sh
python3 scripts/instances.py render-app --instance cronfig > /tmp/cronfig.compose.json
python3 scripts/instances.py render-database > /tmp/mautic-database.compose.json
```

They are not deployment instructions. Before starting anything, provision and inspect the external internal networks, populate and verify the external volumes, create per-database users, supply credentials and complete the gates below. Current ports are proposals and need a fresh collision check at deployment. Veetr already occupies port 8001; starting the candidate there without a migration would fail. The proposed `mautic_veetr` schema and new volumes do not refer to or adopt the current database automatically.

Web starts independently; cron and workers are behind the `jobs` profile. Enable only the roles each instance actually needs after validation. Bound PHP concurrency and stagger cron tasks after measuring memory with all applications present. Initial manifests are intentionally locked to `preparation-only`.

## Local restoration and upgrade checkpoints

1. Capture the two old installations from the web droplet: full application/configuration/media/plugin/theme files (excluding regenerable caches and historical logs) and transaction-consistent MySQL dumps. Store outside Git, owner-only, with checksums. Capture source engine, version and counts without printing customer data or credentials. These online captures are rehearsal material, not the final cutover backup.
2. Restore untouched Mautic 4.4.8 with PHP 8.0 and MySQL 8.0 first. Verify login, asset downloads, forms and database counts. Inventory custom plugins, themes, integrations, uploads, encryption keys and table prefixes. Preserve an untouched snapshot.
3. Rehearse 4 → 5.2 → 6.0 → 7.2.1, including any prerequisite patch releases required by the selected upgrader. Pin exact available intermediate releases and image digests before execution. Do not imply that a bare image swap upgrades persisted application code. M4 uses PHP 7.4/8.0; M5/M6 use PHP 8.1–8.3; M7 requires PHP >=8.2 and MySQL >=8.4. Start with the source database engine and explicitly rehearse the MySQL 8.0 → 8.4 step before M7.
4. For every checkpoint, retain database + matching code/config/media; perform migrations, cache refresh and plugin compatibility work; verify version, migration status, record counts and representative behavior. If a plugin is incompatible, decide its replacement/removal explicitly. Do not silently drop functionality or disable required integrations in the final release.
5. Keep restored application and database containers on internal networks with no outbound route. Bind preview ports to loopback only. Start no cron, workers, event scheduler or queue consumers. Replace production database connections, URLs and mail transport with local values before booting any copy. Use a local mail sink when testing notification content. Network isolation remains necessary for webhooks/plugins even with mail disabled.
6. Browser previews can still load scripts/images/forms with absolute production URLs. Audit/rewrite those references or block production destinations before exercising previews. Never submit local tests to production forms. Raw production configuration remains only in the owner-only capture; running copies use sanitized connection/integration settings while preserving encryption keys required to read existing data.
7. Validate Cronfig's embedded contact/order forms, plugin download asset and notification actions, plus Chimpino's actual integrations discovered during inventory. Record before/after counts for contacts, forms, submissions, emails, campaigns, assets and queued work. Distinguish migration-induced changes from accidental data loss.

References: [Mautic releases](https://mautic.org/releases/), [Mautic 7 upgrade requirements](https://github.com/mautic/mautic/blob/7.x/UPGRADE-7.0.md), [update documentation](https://docs.mautic.org/en/7.1/getting_started/how_to_update_mautic.html). Intermediate releases and their compatibility must be checked at execution time.

## Future deployment and final data synchronization

A successful local copy is a rehearsal, not necessarily the final live dataset. Do not overwrite a current production database with a weeks-old test copy. Determine whether the source has received any writes since capture, including API/cron activity even while its public firewall is closed.

Before cutover, take per-site maintenance, pause only that instance's writers, capture a final coherent database/files backup and rerun the tested migration procedure on it. Keep the source frozen until cutover finishes; if new activity is allowed there, reconcile it explicitly. Import into a new isolated schema/user on the shared MySQL service and prepare matching application volumes. Production restores must be scoped to that schema, never to the whole shared server. Validate SQL dumps contain no unreviewed cross-database statements, grants, users, definers or scheduled events before import.

Route only the selected hostname through host nginx maintenance/upstream changes; validate configuration and reload, never stop nginx globally. The existing legacy `upgrade.sh` still stops nginx and is unsuitable for these deployments. Keep its workflow manual-only until replaced.

Validate login, forms, assets, plugins, background jobs and representative captured email behavior before enabling outbound integrations and reopening traffic. Exercise rollback before cutover. Keep old code/storage/database intact, with a retention decision after acceptance. Automatic rollback is safe only before the new instance accepts writes; afterward, reconcile writes rather than reverting blindly.

Veetr's database migration into the shared service is a separate tested operation, not an implicit side effect of importing Cronfig or Chimpino. All website files and media still need backups even when database backups succeed. Test restoration of one schema without affecting its neighbors.

## Initial capture evidence

Both source installations were copied privately to the local workspace on 2026-10-23. Archive integrity checks succeeded. The dumps contain 118 tables for Cronfig and 108 for Chimpino, matching the source table inventory. Both archives contain configuration and installed dependencies. This is capture verification, not a restore test.

Cronfig includes CronfigBundle. Chimpino includes AiBundle, CronfigBundle, GrapesJsBuilderBundle and StripeBundle. Both have additional themes requiring review. These findings have been added to the manifests; compatibility is not yet established. Credentials, application archives and dumps are outside the repository.

## Remaining implementation gates

- Complete the isolated Chimpino M4 restore and inventory; Cronfig has completed its local M7 rehearsal.
- Turn the recorded Cronfig migration fixes into repeatable, guarded migration runners and rehearse Chimpino separately.
- Build validated application releases containing the correct plugins/themes.
- Verify memory, disk and concurrency on the intended production host size.
- Implement schema-scoped backup/import, per-host locking, per-site nginx switching, readiness verification and rollback.
- Implement protected manual GitHub deployment with instance-specific credentials and no production-data artifacts/logs.
- Rehearse final-copy migrations and verify shared-server permissions/isolation before production use.

## Cronfig rehearsal completed — 2026-10-23

The private local copy was upgraded through Mautic 4.4.8 → 5.2.11 → 6.0.9 → 7.2.1, including MySQL 8.0 → 8.4.5. Matching intermediate checkpoints are retained outside Git. The M7 preview is http://127.0.0.1:8190/s/login while its DDEV project is running.

The clean final dataset retains 69,463 contacts, 99,156 form submissions and 69,302 email statistics records. Login and both public form generators returned HTTP 200. A contact form submission succeeded and its notification was captured by local Mailpit; the database was then restored and verified test-only records removed. The plugin download asset redirected successfully. Required foreign keys were verified after repairing legacy signed-column mismatches.

CronfigBundle was locally ported from its pinned 5.x source. Endpoint checks covered missing/incorrect keys, a harmless successful command and an invalid command. Production Cronfig credentials are blank in the running local copy. The authenticated admin integration and actual external scheduler are still untested; review scheduled commands for M7 compatibility before enabling jobs. See [observed migration fixes](../rehearsal/cronfig-fixes/README.md).

Outbound connections are blocked by the container startup firewall, SMTP uses local capture, MySQL events are disabled and no cron or workers run. The shared DDEV router is unhealthy, so the tested preview uses its direct loopback port. This does not establish production readiness: exact production-image packaging, deployment/rollback rehearsal, final frozen source capture and shared-host capacity checks remain. No production system was changed and no repository changes were pushed.
