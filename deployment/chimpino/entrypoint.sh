#!/usr/bin/env bash
set -Eeuo pipefail
# The upstream image always migrates on web startup, regardless of its migration flag.
# Require the reviewed, already-migrated configuration and start only the web server.
test -s /var/www/html/config/local.php
# Discard image-baked ORM metadata, which was built without this database prefix.
rm -rf -- /var/www/html/var/cache/prod
mkdir -p /var/www/html/var/cache /var/www/html/var/logs
chown -R www-data:www-data /var/www/html/var/cache /var/www/html/var/logs
# Warm once before opening HTTP: parallel cold requests otherwise compete for RAM.
su -s /bin/sh www-data -c 'php -d memory_limit=256M /var/www/html/bin/console cache:warmup --env=prod --no-debug --no-optional-warmers'
exec apache2-foreground
