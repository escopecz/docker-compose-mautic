# Cronfig M7 local rehearsal

This directory contains configuration only, not an installation or production deployment.

The private working project is a restored copy using Mautic 7.2.1, PHP 8.3 and MySQL 8.4, reached through independent M4, M5 and M6 checkpoints. See ../cronfig-fixes/README.md for the observed compatibility fixes and pinned plugin source.

The direct local HTTP preview is port 8190. DDEV's global router is currently unhealthy on this Mac, so use the loopback port; the project's containers and direct endpoint are checked independently. Do not modify other projects to address that router as part of this migration.

Use Mutagen synchronization for the application tree. The custom firewall startup guard, unique database hostname, local SMTP capture and disabled event scheduler remain mandatory. Cron and queue workers are not started. The local config overrides are private: database host ddev-cronfig-migration-m7-db, credentials db/db, database db, site URL http://127.0.0.1:8190, SMTP 127.0.0.1:1025, production Cronfig keys blank. Flush Mutagen before snapshots or host-side packaging.

Before deployment, repeat against a final frozen source copy and test the resulting installation in the exact production Docker image. The upstream release ZIP used by DDEV has a flat layout; the official production image uses a Composer/docroot layout. Do not copy the ZIP application tree over the image's entire application volume. Package custom plugins/themes/media/configuration into the proper image paths and verify both the database migrations and full application behavior. Reapply production connection settings and credentials explicitly; never deploy the local rehearsal configuration.
