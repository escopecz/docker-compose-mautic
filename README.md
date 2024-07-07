# Hosting Mautic 5 on a VPS with Docker Compose

This is a real example of automate hosting Mautic 5 instance(s) on Virtual Private Server (VPS) on [digitalocean.com](https://m.do.co/c/d0ce234a41be)

## Is this for you?

Hosting a web app is not an easy job. You need the technical knowledge and the time to maintain it. This repositry will help but it still requires both especially over time. Please, cosider using services of official [Mautic partners](https://www.mautic.org/mautic-partners) if you just want to use Mautic without any problems and get all the services to make your business succesful. Plus, the partners support the Mautic project and let it grow.

Do you still want to get your hands dirty? That's OK too.

## Why to host this way?

This is a bit different from your normal "execute a bunch of commands" tutorials. This is automated, maintainable deploy process that will keep detailed history of who changed when and why.

It allows you to:
- Upgrade Mautic with 1 line change.
- Downgrade with commit revert.
- Anyone from your team can do this. Avoid the [Bus Factor](https://en.wikipedia.org/wiki/Bus_factor).
- GitHub allows you to set rules that someone needs to approve all changes before they are applied.
- Project management with task boards in place.
- Automatic deployments
- Security scans

The infrastructure that this repository creates lets you start small and scale vertically by increasing DigitalOcean resources and also horizontally by creating more workers to send emails faster.

## How does it work

This repository is a set of configurations and scripts that run automatically on every change and create a Digital Ocean Droplet (VPS), configure it, install a clean Mautic there and everything necessary including HTTPS.

## Requirements

The scripts are there and ready. You need to provide keys and values so it can do all the magic.

- Github to host the configuration and run the deployment (free)
- DigitalOcean to run the VPS where Mautic will run (from $6/month)
- A (sub)domain. This is technically optional, but users won't click on links with just IP addresses.

## What you need to deploy

Here's what you need where to get it to sucessfully deploy Mautic.

## Setup Github Actions Secrets
- https://cloud.digitalocean.com/account/api/tokens
- `DIGITALOCEAN_ACCESS_TOKEN`
- https://cloud.digitalocean.com/account/security
- `DIGITALOCEAN_SSH_FINGERPRINT`

### Virtual Private Server (VPS)

The deployment process will create a VPS (a DigitalOcean droplet) for you with the lowest possible configuration which at this time costs $6/month. It has 1GB of memory and @% GB disk. It will create itself in the New York region. You can modify all these values here. You can always upgrade the memory and disk size. You cannot change the region.

Another option is to create the VPS with the name of `mautic-vps` via the DigitalOcean's user interface where you'll be able to see all the available options. Once you run this deployment process it will use the VPS you've created if the name will match.

## Monitoring

Digitalocean provides nice resource monitoring out of the box. Here is a screenshot how the resource usage looks after fresh installation.

If something is acting up you can see what resources each container is using with command `docker compose stats`. The output looks like this:
```
CONTAINER ID   NAME                    CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O        PIDS
da1d14c8495b   basic-mautic_cron-1     0.01%     25.7MiB / 957.4MiB    2.68%     800kB / 516kB     679MB / 10.8MB   4
5eb3bc650664   basic-mautic_worker-1   0.26%     80.15MiB / 957.4MiB   8.37%     17.5MB / 15.9MB   154MB / 320MB    9
f8089c6149df   basic-mautic_web-1      0.01%     159.4MiB / 957.4MiB   16.65%    2.65MB / 16.4MB   831MB / 56.2MB   13
5d58d082d20c   basic-db-1              1.29%     95.07MiB / 957.4MiB   9.93%     17.9MB / 20.1MB   824MB / 1.04GB   49
```

## Scaling

### Horizontal scaling

### Vertical scaling

## Thank you

This repository wouldn't be possible without the great work that the Mautic community and especially @mollux did at https://github.com/mautic/docker-mautic

## Disclaimer

The links to [Digital Ocean](https://m.do.co/c/d0ce234a41be) are tracked by a referal program. If you are new to Digital Ocean, you'll get $200 in credit and I get $25 credit. You can use any other VPS provider. The steps will be very similar.

## Todos
- [ ] Run `docker compose build` only if necessary to save time. For example if the Dockerfile changes.
- [ ] Test the build before trying to deploy and fail the CI if the build fails.
- [ ] Related to the point above, shall send the built image to some repository like Dockehub? Or GitHub and Digital ocean have their own repositories. Which one? All are limitted to 1 image, all require additional keys which will complicate the setup. But we'd avoid to build the image twice.
- [ ] Adding some service for logging and monitoring of the containers.
- [ ] Use Redis for caching, sessions and queuing.
- [ ] Make it possible to install multiple Mautic instances to the same VPS.
- [ ] Load ballancer.
- [ ] MySql replica.
- [ ] Download the setup-dc.log from the droplet to GH Action files for easier inspection.