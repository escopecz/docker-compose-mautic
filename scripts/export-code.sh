#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd /root/app-new
# Keep the tested Composer code/assets and plugin revision; live state is copied fresh at cutover.
tar --exclude=./config --exclude=./var --exclude=./docroot/media/files --exclude=./docroot/media/images -czf /root/code.tar.gz .
cd /root
sha256sum code.tar.gz > CODE_SHA256SUMS
