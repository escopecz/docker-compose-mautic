#!/bin/bash
set -Eeuo pipefail
# Compose bind-backed secrets retain host ownership. Copy them privately for mysql.
install -d -m 0700 -o mysql -g mysql /run/mysql-secrets
for source in /run/secrets/*; do
    install -m 0400 -o mysql -g mysql "$source" "/run/mysql-secrets/${source##*/}"
done
install -m 0644 /opt/example/init-databases.sh /docker-entrypoint-initdb.d/10-instances.sh
export MYSQL_ROOT_PASSWORD_FILE=/run/mysql-secrets/mysql_root_password
exec /usr/local/bin/docker-entrypoint.sh "$@"
