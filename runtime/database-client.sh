#!/bin/bash
set -Eeuo pipefail
operation=${1:?operation}; database=${2:?database}
[[ $database =~ ^mautic_[a-z][a-z0-9_]{0,23}$ ]]
export MYSQL_PWD="$(cat "/run/mysql-secrets/db_$database")"
case "$operation" in
    dump) exec mysqldump --no-defaults -h127.0.0.1 -u"$database" --single-transaction --routines --triggers --events --hex-blob --no-tablespaces --set-gtid-purged=OFF "$database" ;;
    import) exec mysql --no-defaults --binary-mode=1 --local-infile=0 -h127.0.0.1 -u"$database" "$database" ;;
    query) exec mysql --no-defaults --binary-mode=1 --local-infile=0 -h127.0.0.1 -u"$database" -N "$database" ;;
    *) exit 1 ;;
esac
