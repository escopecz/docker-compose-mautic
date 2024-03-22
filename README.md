# Hosting Mautic 5 on a VPS with Docker Compose

This is a real example of how to host Mautic 5 instance(s) on Virtual Private Server (VPS) such as [digitalocean.com](https://m.do.co/c/d0ce234a41be)

## Create VPS

1. Create an account in [DigitalOcean](https://m.do.co/c/d0ce234a41be) or log in to you existing account.
1. Select Region closest to your contacts
2. Choose image
    - Marketplace
    - Search for and/or select Docker
3. Choose Size: Shared CPU (Basic)
4. CPU optinons: Regular, $6/month
5. Enable backups (yes for production, no for testing)
6. Create the droplet
7. Once created, click on Getting Started
8. Copy the `ssh` command with the IP address to log in via CLI, add the `-A` param to sync your ssh keys

## Setup VPS

In this example we are going for the cheepest option for $6/month. The caviat is that for the installation we need more than 1G memory, so we'll create a swap file that will emulate another gigabyte of memory.

1. Open terminal on your computer and paste the ssh command you copied in the previous section.
2. Copy the `ssh` command with the IP address to log in via CLI, add the `-A` param to sync your ssh keys
10. Add swap file to avoid running out of memory as 1G is not enough
    - `sudo fallocate -l 1G /swapfile`
    - `sudo chmod 600 /swapfile`
    - `sudo mkswap /swapfile`
    - `sudo swapon /swapfile`
    - `echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab`
    - `sudo sysctl vm.swappiness=10`
    - `echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf`
11. `git pull git@github.com:mautic/docker-mautic.git`
12. `cd docker-mautic/examples/basic/`
13. `docker compose up -d`
16. `sudo ufw allow 80`
17. `sudo ufw allow 443`
18. Add site_url config to config/local.php


14. `docker compose ps`
15. `docker compose exec -u www-data -w /var/www/html mautic_web php ./bin/console`

## Setup Github Actions
- https://cloud.digitalocean.com/account/api/tokens
- `DIGITALOCEAN_ACCESS_TOKEN`
- https://cloud.digitalocean.com/account/security
- `DIGITALOCEAN_SSH_FINGERPRINT`
- https://github.com/escopecz/docker-compose-mautic/settings/secrets/actions


## Questions
- What user credentials to log in with?
- How to configure HTTPS?

## Disclaimer

The links to [Digital Ocean](https://m.do.co/c/d0ce234a41be) are tracked by a referal program. If you are new to Digital Ocean, you'll get $200 in credit and I get $25 credit. You can use any other VPS provider. The steps will be very similar.