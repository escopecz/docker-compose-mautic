docker compose build
docker compose up -d mautic_web

echo "## Wait for basic-mautic_web-1 container to be fully running"

while ! docker compose ps mautic_web | tee /tmp/docker_ps_output.txt | grep -q "Up"; do
    echo "### Waiting for mautic_web to be fully running..."
    cat /tmp/docker_ps_output.txt
    sleep 2
done

echo "## Check if Mautic is installed"
if docker compose exec -T mautic_web test -f /var/www/html/config/local.php && docker compose exec -T mautic_web grep -q "site_url" /var/www/html/config/local.php; then
    echo "## Mautic is installed already."
else
    docker compose stop mautic_worker # avoiding https://github.com/mautic/docker-mautic/issues/270

    echo "## Ensure the worker is stopped before installing Mautic"

    while docker compose ps basic-mautic_worker | grep -q "Up"; do
        echo "### Waiting for basic-mautic_worker-1 to stop..."
        sleep 5
    done

    echo "## Installing Mautic..."
    docker compose exec -T -u www-data mautic_web php ./bin/console mautic:install --force --admin_email {{EMAIL_ADDRESS}} --admin_password {{MAUTIC_PASSWORD}} http://{{IP_ADDRESS}}:{{PORT}}
fi

echo "## Starting all the containers"
docker compose up -d