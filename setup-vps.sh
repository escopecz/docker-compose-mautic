#!/bin/bash

# Create a swap file
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# Enable ports for HTTP traffic
sudo ufw allow 80
sudo ufw allow 443

# Install Nginx
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx vim nano
