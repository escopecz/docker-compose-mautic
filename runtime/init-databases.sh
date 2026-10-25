#!/bin/bash
# Called by the official MySQL entrypoint only for a fresh database volume.
(
set -Eeuo pipefail
export MYSQL_PWD="$(cat /run/mysql-secrets/mysql_root_password)"
for secret in /run/mysql-secrets/db_*; do
    database=${secret##*/db_}
    [[ $database =~ ^mautic_[a-z][a-z0-9_]{0,23}$ ]]
    password=$(cat "$secret")
    [[ $password =~ ^[a-f0-9]{48}$ ]]
    grant_database=${database//_/\\_}
    # Escape underscores because database names in GRANT are patterns.
    # Values are validated, and credentials travel on stdin, never argv.
    mysql --protocol=socket -uroot <<SQL
CREATE DATABASE \`$database\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER '$database'@'%' IDENTIFIED BY '$password';
GRANT ALL ON \`$grant_database\`.* TO '$database'@'%';
SQL
done
unset MYSQL_PWD password
)
