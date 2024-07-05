docker compose build
docker compose up -d mautic_web

echo "## Wait for basic-mautic_web-1 container to be fully running"
while ! docker exec basic-mautic_web-1 sh -c 'echo "Container is running"'; do
echo "### Waiting for basic-mautic_web-1 to be fully running..."
sleep 2
done

echo "## Check if Mautic is installed"
if docker-compose exec -T mautic_web test -f /var/www/html/config/local.php && docker-compose exec -T mautic_web grep -q "site_url" /var/www/html/config/local.php; then
echo "## Mautic is installed already."
else
docker stop basic-mautic_worker-1 # avoiding https://github.com/mautic/docker-mautic/issues/270
echo "## Ensure the worker is stopped before installing Mautic"
while docker ps -q --filter name=basic-mautic_worker-1 | grep -q .; do
    echo "### Waiting for basic-mautic_worker-1 to stop..."
    sleep 5
done
echo "## Installing Mautic..."
docker exec -u www-data -w /var/www/html basic-mautic_web-1 php ./bin/console mautic:install --force --admin_email willchange@mautic.org --admin_password MauticR0cks! http://157.230.80.20:8001
fi

echo "## Starting all the containers"
docker compose up -d