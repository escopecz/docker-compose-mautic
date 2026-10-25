#!/bin/bash
set -Eeuo pipefail
umask 027
export MAUTIC_CONSOLE=/var/www/html/bin/console
export MAUTIC_WWW_USER=www-data MAUTIC_WWW_GROUP=www-data
export MAUTIC_VOLUME_CONFIG=/var/www/html/config
export MAUTIC_DB_HOST=mysql MAUTIC_DB_PORT=3306
mkdir -p /var/www/html/config /var/www/html/var/logs /var/www/html/var/cache /var/www/html/var/tmp
chown www-data:www-data /var/www/html/config /var/www/html/var /var/www/html/var/logs /var/www/html/var/cache /var/www/html/var/tmp /var/www/html/docroot/media
php /opt/example/bootstrap.php
case "${DOCKER_MAUTIC_ROLE:-mautic_web}" in
    mautic_web) exec apache2-foreground ;;
    mautic_cron) exec /bin/bash /entrypoint_mautic_cron.sh ;;
    mautic_worker) exec /bin/bash /entrypoint_mautic_worker.sh ;;
    *) echo 'Unknown application role' >&2; exit 1 ;;
esac
