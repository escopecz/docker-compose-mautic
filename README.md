# Multi-instance Mautic deployment preparation

Local preparation now lives in `instances/`, `infrastructure/`, and `scripts/instances.py`. See [the migration plan](docs/multi-instance-migration.md) for the staged local restore and future cutover design. These tools validate inventory and generate candidate Compose files only: they do not connect to servers or deploy.

```sh
python3 scripts/instances.py validate
python3 scripts/instances.py plan --instance cronfig
python3 -m unittest discover -s tests -v
```

The legacy workflow is now manual-only in this local revision. Do not dispatch it for the new instances; it still contains the original single-instance assumptions.

## Legacy Veetr upgrade

This branch targets **only the existing `mautic-veetr-v2` droplet** (`165.232.83.73`). Its web and cron containers share one application and database. Both host nginx domains proxy to that application. The backend must remain bound to `127.0.0.1:8001`.

The workflow replaces the old provisioning action. It never creates, resizes, or reconfigures another production droplet. Pushes do not trigger this legacy workflow in this revision.

## Pinned target

- Mautic 7.2.1, official `7.2.1-20261021-apache` image, pinned by digest; PHP 8.3.36.
- MySQL 8.4, pinned by digest (the Mautic 7 minimum is MySQL 8.4).
- Stripe plugin: a specific tested commit of `chimpino/stripe-plugin`, not a moving branch archive.

Changing a runtime image alone does **not** update this installation: the named application volume masks the code supplied by the image.

## Restore rehearsal

1. Create a disposable Ubuntu 24.04 DigitalOcean droplet, 2 CPUs / 4 GB RAM, in Amsterdam. It incurs usage charges until deletion.
2. Briefly stop Mautic web and cron, dump the database, archive the complete mounted application/configuration/media, verify archive checksums, then resume the current application.
3. Transfer the backup **directly between the DigitalOcean droplets** using a temporary SSH key. Customer data and configuration secrets do not pass through the GitHub runner or become Actions artifacts.
4. Restore the database and old application on the test droplet, then migrate a copy to the pinned Mautic 7 image and Stripe revision. Application containers use an internal Docker network without outbound access; cron and workers are not started on the test copy.
5. Retain private failure diagnostics alongside the root-only production backup. Delete the temporary transfer key and test droplet on success or failure. No DigitalOcean snapshot or automatic backup is created for the test droplet.

For another rehearsal against the same snapshot, dispatch the workflow with `recovery_run` set to the verified backup run ID (for example `39860279591-1`). This reuses the backup without stopping production again. Production cutover still requires a fresh backup.

If the runner itself disappears or cleanup reports failure, check DigitalOcean for the exact run-scoped name `mautic-veetr-v2-test-RUN_ID-ATTEMPT`. Do not delete other droplets. The workflow confirms deletion through the API.

## Production cutover and recovery

The cutover script is deliberately scoped to the observed Mautic 6.0.5 installation. Before migration it obtains another coherent backup, prepares separate application, config, media, and database volumes, and preserves the original volumes and runtime images.

During cutover nginx is stopped so the old database and new database cannot receive competing live requests. Database migration, plugin discovery, application version, PHP version, and loopback login checks precede reopening traffic. A failure before traffic reopens restores the original Compose configuration and untouched volumes. After traffic reopens, automatic rollback is disabled to avoid discarding new writes.

Root-only recovery material is stored in `/root/mautic-upgrade-RUN_ID-ATTEMPT-final`. The original `/root/mautic-php-backup-20261022` backup and its rollback image are additional recovery options; the fresh backup is the relevant pre-upgrade recovery point.

Do not run `docker compose down -v`, prune Docker volumes, or delete the original volumes until the upgrade has been accepted. A rollback after production resumes needs a maintenance window and a decision about handling writes made since cutover.

All production changes run through GitHub Actions. Read-only SSH inspection may be used for diagnosis. No production database contents, environment files, backup archives, or detailed application logs should be posted to public job logs or artifacts.
