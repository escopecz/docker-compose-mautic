#!/usr/bin/env bash
set -Eeuo pipefail
# Fail closed before PHP/web services start, including after a DDEV restart.
sudo iptables -P OUTPUT DROP
sudo ip6tables -P OUTPUT DROP
sudo iptables -F OUTPUT
sudo ip6tables -F OUTPUT
sudo iptables -A OUTPUT -o lo -j ACCEPT
sudo ip6tables -A OUTPUT -o lo -j ACCEPT
sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo ip6tables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
for address in $(getent ahostsv4 ddev-cronfig-migration-m4-db | awk '{print $1}' | sort -u); do
  sudo iptables -A OUTPUT -d "$address" -p tcp --dport 3306 -j ACCEPT
done
