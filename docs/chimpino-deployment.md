# Chimpino migration and scoped deployment

The Chimpino candidate targets Mautic 7.2.1 on the patched official PHP 8.3 image already used by Cronfig. Its web container listens on loopback port 8003, uses the separate `mautic_chimpino` schema/user on the existing MySQL service, and has its own internal database network. No local cron or queue worker starts during deployment.

The AI plugin is excluded at the owner's request. Historical prompt rows are retained; do not drop its tables during schema cleanup. Stripe and Cronfig remain required integrations. All application data and credentials stay in private migration storage, outside this repository and GitHub Actions.

Rehearse M4 → M5 → M6 → M7 locally with database/file checkpoints, outbound traffic blocked, local mail capture, and MySQL events disabled. Validate the source's empty table prefix, contact/submission/email counts, Stripe events, form routes, plugin authentication and email behavior. Freeze only the old Chimpino installation and verify the final source before activation.

The workflow selects `instance=chimpino`; the existing `cronfig_action` input selects its phase. Stage refuses an existing destination schema. Activation requires final-source evidence, passes readiness, installs private daily backups at 03:37 server time, and leaves DNS cutover to the operator. Other applications and the shared database are not restarted.

Unlike Cronfig, authoritative DNS for `chimpino.com` is at GoDaddy. Issue the new certificate directly on DigitalOcean using a temporary DNS challenge at GoDaddy; the private key never leaves the destination. The `chimpino-acme-hook.py` helper publishes only the challenge value in a root-only file and checks both authoritative nameservers. The workflow requires that certificate before staging and never attempts to change this domain through DigitalOcean DNS.

After activation and verification, update only the `m.chimpino.com` A record at GoDaddy to `165.232.83.73`. Preserve all other records. Once public resolution reaches the destination, use `renew-certificate` to switch renewal to webroot and validate a dry run. Existing canceled Cronfig schedules remain paused until a separate restart decision after cutover.

After the new instance accepts writes, never automatically restore the old database. Maintenance closes only the selected hostname while preserving its data. Retain the original source and private checkpoints until acceptance.

The Mautic 7.2.1 image omits the compiled GrapesJS editor files. Build the editor from the matching source with `composer gjs-build` and include its `Assets/library/js/dist` directory as `grapesjs-dist` in the release payload and checksum manifest. Deployment copies these files into `runtime/grapesjs-dist` and mounts them read-only, preserving them across container recreation. Existing installations received the matching tested assets on 2026-10-23.
