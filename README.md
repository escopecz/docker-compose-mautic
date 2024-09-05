# Hosting Mautic 5 on a VPS with Docker Compose

This is a working example of automate hosting Mautic 5 instance(s) on Virtual Private Server (VPS) on [digitalocean.com](https://m.do.co/c/d0ce234a41be)

## Mautic Conference Global 2024 video about this project

[![Docker Compose for Mautic introduced in the Mautic Conference Global 2024](https://github.com/user-attachments/assets/7841185f-5137-4130-9f23-6871606f4c7d)](https://www.youtube.com/watch?v=lzyjbUKZZlY)

## Is this for you?

Hosting a web app is not an easy job. You need the technical knowledge and the time to maintain it. This repositry will help but it still requires both. Especially over time.

The easiest option is to start your 2 week trial today: https://m.mautic.org/mautic-start-your-trial

Or if you like more choices consider the official [Mautic partners](https://www.mautic.org/mautic-partners) if you just want to use Mautic without any problems and get all the services to make your business succesful.

By using both these options you will get the bet service possible and support the Mautic project.

Do you still want to get your hands dirty? That's OK too.

## Why to deploy this way?

This is a bit different from your normal "execute a bunch of commands" tutorials. This is automated, maintainable deploy process that will keep detailed history of who changed when and why.

It allows you to:
- Install Mautic within 10 minutes.
- Upgrade Mautic with 1 line change.
- Downgrade with commit revert.
- Install themes and plugins via Composer.
- Anyone from your team can do this. Avoid the [Bus Factor](https://en.wikipedia.org/wiki/Bus_factor). GitHub allows you to set rules that someone needs to approve all changes before they are applied.
- Project management with task boards in place.
- Security scans.

The infrastructure that this repository creates lets you start small and scale [vertically](#vertical-scaling) by increasing DigitalOcean resources and also [horizontally](#horizontal-scaling) by creating more workers to send emails faster.

## Requirements

The scripts are there and ready. You need to provide keys and values so it can do all the magic.

- Github to host the configuration and run the deployment (free)
- DigitalOcean to run the VPS where Mautic will run (from $6/month)
- A (sub)domain. This is technically optional, but users won't click on links with just IP addresses.

## What you need to deploy

In order to deploy Mautic, you need a few "secrets" and "variables" so it can perform all the tasks. You cannot access the value it is saved.

Github Actions is the tool that will take the code from this repository and executes it. That is the deployment process that will create the VPS, configures it and install Mautic with Docker Compose inside.

## Setup Github Actions Secrets

The secrets are values you don't want anyone else to see.

- `SSH_PRIVATE_KEY` is used to access the VPS via SSH by Github Actions, the deployment process. You can use the one you already have in `~/.ssh` folder or generate a new one. Follow [the official documentation](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys) to generate it and add it to the DigitalOcean configuration.
- Once you have stored the SSH key to the DigitalOcean configuration, copy the Fingerprint for `DIGITALOCEAN_SSH_FINGERPRINT` at https://cloud.digitalocean.com/account/security
- Create `DIGITALOCEAN_ACCESS_TOKEN` at https://cloud.digitalocean.com/account/api/tokens
- `MAUTIC_PASSWORD` is an admin password to log in to the freshly installed Mautic. Store it to your password manager.

This is how the secrets section should look like:
![Github Actions Secrets](https://github.com/escopecz/docker-compose-mautic/assets/1235442/afbf1ea0-e16b-4bcf-a58d-90ba03c63204)

## Setup Github Actions Variables

The variables are values that is OK to be visible. You can edit the vaule after it is saved.

- `EMAIL_ADDRESS` will be used to create a Mautic admin user and you'll use it to log in. It is also used to build the SSL certificates.
- `DOMAIN` is the domain that will be used to access your Mautic. Do not add it at first. Add it only after you know the VPS IP address and after you've pointed the DNS record to that IP address. If the DOMAIN is unknown, you can still access your new Mautic via the IP address.

Example:
![Github Actions Variables](https://github.com/escopecz/docker-compose-mautic/assets/1235442/bfc5df49-55b0-4a1d-a8ee-181429bdf244)

## How does it work

This repository is a set of configurations and scripts that run automatically on every change and create a Digital Ocean Droplet (VPS), configure it, install a clean Mautic there and everything necessary including HTTPS.

![Mautic Docker Compose diagram](Mautic-dc-diagram.drawio.svg)

### Virtual Private Server (VPS)

The deployment process will create a VPS (a DigitalOcean droplet) for you with the lowest possible configuration which at this time costs $6/month. It has 1GB of memory and @% GB disk. It will create itself in the New York region. You can modify all these values here. You can always upgrade the memory and disk size. You cannot change the region.

Another option is to create the VPS with the name of `mautic-vps` via the DigitalOcean's user interface where you'll be able to see all the available options. Once you run this deployment process it will use the VPS you've created if the name will match.

### Nginx

Nginx is a server like Apache. This server is installed directly on the VPS and the only reason is to handle SSL. I other words, to handle the certificates necessary for HTTPS. The `mautic_web` container actually have its own server to handle HTTP requests. In this case it is Apache.

### Docker Compose vs Docker

**Docker** is a program that can manage lightweight containers. It serves the same role as virtual machines. The difference is that containers are lighter in size and so creating them takes less time and they do not take that much space.

A container is a list or a recipe of commands that needs to be executed to build whatever you want the container to do. In this case we take [this Dockerfile](https://github.com/mautic/docker-mautic/blob/mautic5/apache/Dockerfile) as a base and define [our own Dockerfile](Dockerfile) sprinkle a few more commands on top of it so we could install themes and plugins.

**Docker Compose** enables simplified networking between the containers and [1 config file](docker-compose.yml) where all that interconnection is described.

The [docker-compose.yml](docker-compose.yml) in this repository was copied from https://github.com/mautic/docker-mautic/tree/mautic5/examples/basic

### Containers

There are 4 containers created with the deployment process by default.

#### mautic_web

This container is the only public container. Meaning it's the only container accessible with HTTP requests. It's the one that we interact with via a browser.

#### mautic_cron

This container's whole purpose is to run cron commands. The crontab is created by [this script](https://github.com/mautic/docker-mautic/blob/mautic5/common/entrypoint_mautic_cron.sh) and modifiable on the VPS as it's a shared volume. However, to continue the philosophy of this repository, it should be created and commited to this repository instead. See the Todo section bellow.

#### mautic_worker

Mautic 5 started using workers for sending emails. This container is a worker that is waiting for the email jobs and executing the email send. If you want to speed up the email send speed, you can configure the [`replicas`](docker-compose.yml) configuration and the deployment process will take care of it.

### db

`db` is a container running MySql. All other containers are using this one to store and read data. The data are stored as a volume so they are not lost when this container is deleted.

### Volumes

Volumes are basically files and directories that are shared between a container and its host computer. Containers are stateless by default so when a container is deleted, it deletes all its files as well. If there are some files we want to keep we need to store them to the host computer. Hence that's why we have volumes in our setup. For example for files, images that you upload to Mautic. But also for the database.

## How to install themes and plugins

One of the goals of this deployment is to have a trace of everything related to the Mautic instance configuration. Installing a plugin or a theme can break your Mautic so it's good to have a way to roll back if it happens. And to have a trace of who installed what, when and why is also great to have. Git gives us all that.

In the [Dockerfile](Dockerfile) there is an example of how to install a package. In this case it is a [`chimpino/theme-air`](https://chimpino.com/themes) theme. If you need to install anyting else, you'll just add a new line with the package you need and commit this one line change.


## Cron jobs

Cron job configuration is usually a big pain to setup for newcomers. In this case you can manage them in this repository in the [cron/mautic](cron/mautic) file. Make a change, commit and it will deploy to the server automatically. Most of the cron jobs are prepared there anyway so you may not need to make any change.

## HTTPS

SSL certificate management is also a pain to manage. In this case you just point the domain DNS A record to the VPS IP address, configure the DOMAIN variable in the Github repository Github Actions and re-run the latest job. Everything else is automated.

## Monitoring

Digitalocean provides nice resource monitoring out of the box. Here is a screenshot how the resource usage looks after fresh installation.

![DigitalOcean monitoring](https://github.com/escopecz/docker-compose-mautic/assets/1235442/3f0d8dea-3321-47c6-9176-c0fe71f8204d)

If something is acting up you can see what resources each container is using with command:

`docker compose stats`

The output looks like this:
```
CONTAINER ID   NAME                    CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O        PIDS
da1d14c8495b   basic-mautic_cron-1     0.01%     25.7MiB / 957.4MiB    2.68%     800kB / 516kB     679MB / 10.8MB   4
5eb3bc650664   basic-mautic_worker-1   0.26%     80.15MiB / 957.4MiB   8.37%     17.5MB / 15.9MB   154MB / 320MB    9
f8089c6149df   basic-mautic_web-1      0.01%     159.4MiB / 957.4MiB   16.65%    2.65MB / 16.4MB   831MB / 56.2MB   13
5d58d082d20c   basic-db-1              1.29%     95.07MiB / 957.4MiB   9.93%     17.9MB / 20.1MB   824MB / 1.04GB   49
```

## Debugging

You may need to execute some command in the VPS or one of the nodes from time to time. Or debug what's happening like with the monitoring above. Here's a list of useful commands.

For all `docker compose` commands navigate to the folder where this deployment script is pushing the `docker-compose.yml` file. From this folder you can use the `docker compose` commands.

`cd /var/www/`

### Online terminal

You can controll everything from the browser. DigitalOcean has this nice feature that opens a terminal directly from the administration. All you need is a browser. Follow this screenshot:

### List all containers

`docker compose ps`

Example output:
```
root@mautic-vps:/var/www# docker compose ps
NAME                    IMAGE                 COMMAND                  SERVICE         CREATED          STATUS                    PORTS
basic-db-1              mysql:8.0             "docker-entrypoint.s…"   db              40 minutes ago   Up 40 minutes (healthy)   3306/tcp, 33060/tcp
basic-mautic_cron-1     basic-mautic_cron     "/entrypoint.sh apac…"   mautic_cron     40 minutes ago   Up 39 minutes             80/tcp
basic-mautic_web-1      basic-mautic_web      "/entrypoint.sh apac…"   mautic_web      40 minutes ago   Up 40 minutes (healthy)   0.0.0.0:8001->80/tcp, :::8001->80/tcp
basic-mautic_worker-1   basic-mautic_worker   "/entrypoint.sh apac…"   mautic_worker   40 minutes ago   Up 27 minutes             80/tcp
```

### Getting the deploy script logs

If there is a problem with the deployment, you can see it in the logs that are being downloaded and attached to each Github Action job as an artifact. So you can see how the deployment went without logging into the server. Just go to the summary of the job you are interested in and download the `setup-dc-log` artifact for inspection.

### Getting the container logs

Perhaps you want to see how the `mautic_cron` container is working. Or debug why some command is not working perhaps. In that case execute

`docker compose logs mautic_cron`

You can do the same for any of the containers that you get from the `docker compose ps` command above.

### Executing a command in a container

The best way is to log inside the container with a command like

`docker compose exec -it -u www-data mautic_cron bash`

Notice that the user, host and folder changed in your next line in the terminal. It means you are inside the container. Here is how the output looks like:

Notice you are in the `docroot` directory. That's the directory where the publicly accessible files are. If you want to run some `bin/console` command for example, you have to go one directory up with `cd ..`.

Example:
```
root@mautic-vps:/var/www# docker compose exec -it -u www-data mautic_cron bash
www-data@b465afe49214:~/html/docroot$ cd ..
www-data@b465afe49214:~/html$ php bin/console cache:clear

 // Clearing the cache for the prod environment with debug false                                                        

 [OK] Cache for the "prod" environment (debug=false) was successfully cleared.                                          

www-data@b465afe49214:~/html$ exit
exit
root@mautic-vps:/var/www#
```


## Scaling

This setup will allow you to start small, monitor the resources and if some CPU, RAM, Disk or Transfer will start hitting a limit then you can scale horizontically. If the emails are sending too slow, you can scale vertically.

### Horizontal scaling

You can resize your VPS any time and add resources as you see fit. Example:
![Resizing a VPS](https://github.com/escopecz/docker-compose-mautic/assets/1235442/2fac709d-1d0b-4771-b408-5563de19a001)

### Vertical scaling

This setup currently allows to vertically scale the worker containers. You can increase the [`replicas`](docker-compose.yml) and speed up the email sending.

_Future glance: In Mautic 5 the workers are "just" sending emails, but the cron jobs should be slowly moved to workers as well. This deployment setup can also add a load ballancer and in that case we will be able to scale the web containers. Also a database read only replica can be added if the SQL requests are the bottleneck._

## Thank you

This repository wouldn't be possible without the great work that the Mautic community and especially @mollux did at https://github.com/mautic/docker-mautic

## Disclaimer

The links to [Digital Ocean](https://m.do.co/c/d0ce234a41be) in this readme are tracked by a referal program. If you are new to Digital Ocean, you'll get $200 in credit and I get $25 credit. You can use access the DigitalOcean website any other way to avoid this referal.

## Todos
- [ ] Run `docker compose build` only if necessary to save time. For example if the Dockerfile changes.
- [ ] Test the build before trying to deploy and fail the CI if the build fails.
- [ ] Related to the point above, shall send the built image to some repository like Dockehub? Or GitHub and Digital ocean have their own repositories. Which one? All are limitted to 1 image, all require additional keys which will complicate the setup. But we'd avoid to build the image twice.
- [ ] Adding some service for logging and monitoring of the containers.
- [ ] Use Redis for caching, sessions and queuing.
- [ ] Make it possible to install multiple Mautic instances to the same VPS.
- [ ] Load ballancer.
- [ ] MySql replica.
- [x] Download the setup-dc.log from the droplet to GH Action files for easier inspection.
- [x] Make the crontab configurable in this repository.
