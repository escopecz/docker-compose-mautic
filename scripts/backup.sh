#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $(hostname) == mautic-veetr-v2 ]]
cd /var/www
exec 9>/run/mautic-upgrade.lock
flock -n 9
backup=/root/mautic-upgrade-${1:?run id}
[[ ! -e "$backup" ]]
[[ $(df --output=avail -B1 / | tail -1) -gt 600000000 ]]
mkdir -m 700 "$backup"
cp docker-compose.yml .mautic_env "$backup/"
[ ! -f .env ] || cp .env "$backup/"
docker inspect mautic_web --format '{{.Config.Image}}' > "$backup/runtime-image"
docker inspect mautic_db --format '{{.Image}}' > "$backup/database-image"
# Quiesce both writers for one consistent database and filesystem snapshot.
resume() { docker start mautic_web mautic_cron >/dev/null; }
trap resume EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
docker stop -t 90 mautic_cron mautic_web >/dev/null
docker exec mautic_db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --events --hex-blob --set-gtid-purged=OFF --no-tablespaces --databases "$MYSQL_DATABASE"' 2>"$backup/dump.log" | gzip > "$backup/db.sql.gz"
gzip -t "$backup/db.sql.gz"
zcat "$backup/db.sql.gz" | tail -3 | grep -q 'Dump completed'
docker run --rm --volumes-from mautic_web --entrypoint tar "$(cat "$backup/runtime-image")" -C /var/www/html --exclude=./var/cache --exclude=./var/logs -czf - . > "$backup/app.tar.gz"
tar -tzf "$backup/app.tar.gz" >/dev/null
(cd "$backup" && sha256sum db.sql.gz app.tar.gz > SHA256SUMS)
echo "Coherent backup complete: $backup"

if [[ ${2:-} == keep-stopped ]]; then trap - EXIT; fi
