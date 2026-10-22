#!/usr/bin/env bash
# Run only through the deployment workflow, after a successful restore rehearsal.
set -Eeuo pipefail
umask 077
[[ $(hostname) == mautic-veetr-v2 ]]
run=${1:?run id}
[[ $run =~ ^[0-9]+-[0-9]+$ ]]
: "${TARGET_IMAGE:?}" "${MYSQL_IMAGE:?}"
cd /var/www
wait_cron() {
  for attempt in $(seq 1 30); do
    if docker exec mautic_cron pgrep -x cron >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  return 1
}
version=$(docker exec -w /var/www/html mautic_web php bin/console --version)
if [[ $version == 'Mautic 7.2.1 '* ]]; then
  [[ $(docker inspect mautic_web --format '{{.Config.Image}}') == "$TARGET_IMAGE" ]]
  [[ $(docker inspect mautic_db --format '{{.Config.Image}}') == "$MYSQL_IMAGE" ]]
  docker compose -p www up -d db mautic mautic_cron
  docker exec mautic_cron php -r 'if (version_compare(PHP_VERSION,"8.3.36","<")) exit(1);'
  wait_cron
  curl -fsS --max-time 10 -H "Host: m.veetr.com" -H "X-Forwarded-Proto: https" -o /dev/null http://127.0.0.1:8001/s/login
  echo 'Target Mautic version is already installed; verified web and cron without repeating migration.'
  exit 0
fi
[[ $version == 'Mautic 6.0.5 '* ]] || { echo 'Unexpected source version; refusing untested migration'; exit 1; }
[[ $(docker inspect mautic_db --format '{{range .Mounts}}{{if eq .Destination "/var/lib/mysql"}}{{.Name}}{{end}}{{end}}') == www_mysql_data ]]
exec 8>/run/mautic-cutover.lock
flock -n 8
stage=/root/mautic-stage-$run
backup=/root/mautic-upgrade-$run-final
[[ -f "$stage/code.tar.gz" && -f "$stage/SHA256SUMS" ]]
(cd "$stage" && sha256sum -c SHA256SUMS)
# Only obsolete, unused image revisions observed on this server. Never prune volumes.
for obsolete in mautic/mautic:6.0.5-apache e209460f8a1e; do
  if docker image inspect "$obsolete" >/dev/null 2>&1; then
    docker image rm "$obsolete" || true
  fi
done
docker pull "$TARGET_IMAGE"
docker pull "$MYSQL_IMAGE"
if [[ $(df --output=avail -B1 / | tail -1) -le 3200000000 ]]; then
  # Bound archived system logs only; preserve application logs and recovery data.
  journalctl --vacuum-size=1G
fi
[[ $(df --output=avail -B1 / | tail -1) -gt 3200000000 ]] || { echo 'Insufficient free disk for parallel recovery volumes'; exit 1; }
committed=false
maintenance=false
rollback() {
  result=$?
  if $maintenance && ! $committed; then
    echo 'Cutover failed; restoring original compose and untouched data volumes.'
    mapfile -t migration_containers < <(docker ps -q --filter "label=mautic-upgrade-run=$run")
    if (( ${#migration_containers[@]} )); then docker stop -t 10 "${migration_containers[@]}" || true; fi
    docker compose -p www stop mautic_cron mautic db || true
    if [[ -f "$backup/docker-compose.yml" ]]; then
      cp "$backup/docker-compose.yml" /var/www/docker-compose.yml
    fi
    docker compose -p www up -d db mautic mautic_cron
  fi
  if $maintenance; then systemctl start nginx; fi
  exit "$result"
}
trap rollback EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
# Both configured nginx virtual hosts point to this Mautic backend.
systemctl stop nginx
maintenance=true
bash "$stage/backup.sh" "$run-final" keep-stopped
# Keep original volumes untouched. Prepare separate volumes for the new application.
for part in data config media mysql; do docker volume create "www_m7_${run}_${part}" >/dev/null; done
path_for() { docker volume inspect "$1" --format '{{.Mountpoint}}'; }
newroot=$(path_for "www_m7_${run}_data")
oldroot=$(path_for www_mautic_data)
tar -xzf "$stage/code.tar.gz" -C "$newroot"
mkdir -p "$newroot/var/cache" "$newroot/var/logs" "$newroot/var/tmp"
python3 "$stage/preserve-custom.py" "$oldroot" "$newroot" --skip-stripe
cp -a "$(path_for www_mautic_config)/." "$(path_for "www_m7_${run}_config")/"
cp -a "$(path_for www_mautic_media)/." "$(path_for "www_m7_${run}_media")/"
chown -R 33:33 "$newroot" "$(path_for "www_m7_${run}_config")" "$(path_for "www_m7_${run}_media")"
docker compose -p www config --format json > "$stage/previous-compose.json"
python3 "$stage/compose-upgrade.py" "$stage/previous-compose.json" "$stage/next-compose.json" "$run"
docker compose -p www -f "$stage/next-compose.json" config --quiet
install -m 600 "$stage/next-compose.json" /var/www/docker-compose.yml
# Shut the old database down cleanly; its complete original volume is retained.
docker compose -p www up -d db
ready=false
for attempt in $(seq 1 90); do
  if docker exec mautic_db sh -c 'mysql --protocol=TCP -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1"' >/dev/null 2>&1; then ready=true; break; fi
  sleep 2
done
$ready
gzip -dc "$backup/db.sql.gz" | docker exec -i mautic_db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'
console() { docker compose -p www run --rm --no-deps --label "mautic-upgrade-run=$run" --user 33:33 -w /var/www/html --entrypoint php mautic -d memory_limit=768M bin/console "$@"; }
console cache:clear --no-interaction
console doctrine:migrations:migrate --no-interaction -vv
console mautic:update:apply --finish --no-interaction
console mautic:plugins:install --no-interaction
console cache:clear --no-interaction
console --version | grep 'Mautic 7.2.1'
console debug:router stripe_webhook
console doctrine:query:sql 'SELECT COUNT(*) FROM users' --no-interaction
docker compose -p www up -d mautic
ready=false
for attempt in $(seq 1 90); do
  if [[ $(docker inspect mautic_web --format '{{.State.Health.Status}}') == healthy ]] && curl -fsS --max-time 10 -H "Host: m.veetr.com" -H "X-Forwarded-Proto: https" -o /dev/null http://127.0.0.1:8001/s/login; then ready=true; break; fi
  sleep 2
done
$ready
docker exec mautic_web php -r 'if (version_compare(PHP_VERSION,"8.3.36","<")) exit(1); echo PHP_VERSION,PHP_EOL;'
# Reopening traffic is the commit point. Never automatically undo subsequent writes.
committed=true
systemctl start nginx
docker compose -p www up -d mautic_cron
docker exec mautic_cron php -r 'if (version_compare(PHP_VERSION,"8.3.36","<")) exit(1); echo PHP_VERSION,PHP_EOL;'
wait_cron
console doctrine:migrations:status --no-interaction
printf 'Upgrade complete. Original volumes and recovery compose retained in %s\n' "$backup"
