#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
diagnostics() {
  result=$?
  if (( result != 0 )); then
    echo "Rehearsal failed; private application diagnostics follow."
    find "$RUNNER_TEMP/app-new/var/logs" -maxdepth 1 -type f -exec tail -n 100 {} + || true
    docker logs rehearsal-db 2>&1 || true
    docker logs rehearsal-web 2>&1 || true
  fi
  exit "$result"
}
trap diagnostics EXIT
recovery=$RUNNER_TEMP/recovery
old=$RUNNER_TEMP/app-old
new=$RUNNER_TEMP/app-new
mkdir -p "$old" "$new"
sudo tar -xzf "$recovery/app.tar.gz" -C "$old"
old_image=$(cat "$recovery/runtime-image")
docker pull "$old_image" >/dev/null
docker pull "$TARGET_IMAGE" >/dev/null
docker pull "$MYSQL_IMAGE" >/dev/null
# No SMTP, webhook, scheduled tasks or other production integrations can be reached.
docker network create --internal rehearsal >/dev/null
docker run -d --name rehearsal-db --network rehearsal --network-alias mysql --network-alias db --env-file "$recovery/.mautic_env" "$MYSQL_IMAGE" >/dev/null
ready=false
for i in $(seq 1 90); do
  if docker exec rehearsal-db sh -c 'mysql --protocol=TCP -h127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1"' >/dev/null 2>&1; then ready=true; break; fi
  sleep 2
done
$ready
echo 'Restoring database backup.'
gzip -dc "$recovery/db.sql.gz" | docker exec -i rehearsal-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'
console() {
  docker run --rm --network rehearsal --env-file "$recovery/.mautic_env" --user 33:33 \
    -v "$1:/var/www/html" -v "$1/config:/var/www/html/config" \
    -v "$1/docroot/media/files:/var/www/html/docroot/media/files" \
    -v "$1/docroot/media/images:/var/www/html/docroot/media/images" \
    -v "$1/var/logs:/var/www/html/var/logs" \
    -w /var/www/html --entrypoint php "$2" "${@:3}"
}
sudo mkdir -p "$old/var/cache" "$old/var/logs"
sudo chown -R 33:33 "$old"
console "$old" "$old_image" bin/console --version
console "$old" "$old_image" bin/console doctrine:query:sql 'SELECT COUNT(*) FROM users' --no-interaction
# Official M7 image supplies the complete Composer installation and compiled assets.
id=$(docker create "$TARGET_IMAGE")
docker cp "$id:/var/www/html/." "$new/"
docker rm "$id" >/dev/null
sudo cp -a "$old/config/." "$new/config/"
sudo cp -a "$old/docroot/media/files/." "$new/docroot/media/files/"
sudo cp -a "$old/docroot/media/images/." "$new/docroot/media/images/"
# Preserve custom plugins and themes; Composer-managed packages come from M7.
sudo python3 scripts/preserve-custom.py "$old" "$new"
sudo cp -a /root/plugin/. "$new/docroot/plugins/StripeBundle/"
sudo mkdir -p "$new/var/cache" "$new/var/logs"
sudo chown -R 33:33 "$new"
console "$new" "$TARGET_IMAGE" -r 'if (version_compare(PHP_VERSION,"8.3.36","<")) exit(1); echo "PHP ",PHP_VERSION,PHP_EOL;'
console "$new" "$TARGET_IMAGE" bin/console cache:clear --no-interaction
console "$new" "$TARGET_IMAGE" bin/console doctrine:migrations:migrate --no-interaction -vv
console "$new" "$TARGET_IMAGE" bin/console mautic:update:apply --finish --no-interaction
console "$new" "$TARGET_IMAGE" bin/console mautic:plugins:install --no-interaction
console "$new" "$TARGET_IMAGE" bin/console cache:clear --no-interaction
console "$new" "$TARGET_IMAGE" bin/console --version | grep 'Mautic 7.2.1'
console "$new" "$TARGET_IMAGE" bin/console debug:router stripe_webhook
console "$new" "$TARGET_IMAGE" bin/console doctrine:query:sql 'SELECT COUNT(*) FROM users' --no-interaction
console "$new" "$TARGET_IMAGE" bin/console doctrine:migrations:status --no-interaction
# Exercise the real web entry point without publishing a port or enabling cron.
docker run -d --name rehearsal-web --network rehearsal --env-file "$recovery/.mautic_env" \
  -e DOCKER_MAUTIC_ROLE=mautic_web -e DOCKER_MAUTIC_RUN_MIGRATIONS=false \
  -v "$new:/var/www/html" -v "$new/config:/var/www/html/config" \
  -v "$new/docroot/media/files:/var/www/html/docroot/media/files" \
  -v "$new/docroot/media/images:/var/www/html/docroot/media/images" \
  -v "$new/var/logs:/var/www/html/var/logs" "$TARGET_IMAGE" >/dev/null
ready=false
for attempt in $(seq 1 60); do
  if docker exec rehearsal-web sh -c 'curl --fail --silent --max-time 5 -H "Host: m.veetr.com" -H "X-Forwarded-Proto: https" -o /tmp/rehearsal-login.html http://127.0.0.1/s/login && grep -q "name=\"_username\"" /tmp/rehearsal-login.html'; then ready=true; break; fi
  sleep 2
done
$ready
docker stop rehearsal-web >/dev/null
printf 'Restored M6 and migrated M7 with Stripe successfully. Production remains on its original application.\n' >> "$GITHUB_STEP_SUMMARY"
