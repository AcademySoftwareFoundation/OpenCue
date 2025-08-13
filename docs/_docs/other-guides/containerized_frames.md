---
title: "Running RQD at Docker mode"
layout: default
parent: Other Guides
nav_order: 35
linkTitle: "Running RQD at Docker mode"
date: 2024-11-06
description: >
  Running rqd with docker mode so that each frame is launched
  at its own container
---

# Running RQD Frames in Isolated Docker Containers

### Run RQD frames in separate Docker containers with setup and swarm guidance

---

This guide describes how to configure rqd to run each frame on its own container

## Configuration

The following properties are required on rqd.conf to make use of this feature:

```toml
[docker.config]
# Setting this to True requires all the additional "docker.[]" sections to be filled
RUN_ON_DOCKER=True
DOCKER_SHELL_PATH=/usr/bin/sh

# This section is only required if RUN_ON_DOCKER=True
# List of volume mounts following docker run's format, but replacing = with :
[docker.mounts]
TEMP=type:bind,source:/tmp,target:/tmp,bind-propagation:slave
NET=type:bind,source:/net,target:/net,bind-propagation:slave

# This section is only required if RUN_ON_DOCKER=True
#  - keys represent OSs this rqd is capable of executing jobs in
#  - values are docker image tags
[docker.images]
centos7=centos7.3:latest
rocky9=rocky9.3:latest
```

Each key reported under `[docker.images]` will be used as an OS reported to Cuebot by RQD.
In the example above, rqd will report its OS as `centos7,rocky9`. Whenever cuebot finds a list on
the OS fields, it will interpret this RQD is capable of launching images for any of the OSs on the list.

## Requirements

The environment your RQD instance is running on needs to have Docker installed and RQD's user needs to
have permissions to execute docker commands. Besides that, the optional pip requirement `docker` needs
to be added to requirements.txt.

## Docker swarm setup tips

If you're planning to run RQD itself on docker, docker swarm has some limitations that need to be taken
into consideration for this setup.

### Docker-in-docker is not recommended

If you want to know the reason why it is not recommend, read this
[article](https://jpetazzo.github.io/2015/09/03/do-not-use-docker-in-docker-for-ci/).
 To avoid this scenario, you should mount in docker.sock with
`--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock,ro`.
This will give rqd in your container access to the docker daemon running on the host.
Besides that, your should also run with `--pid=host` because rqd needs access to the
processes launched from inside of the frame container with their original pid.

But this brings with it one complications. Docker swarm mode doesn't support `--pid=host`
(See this [Issue](https://github.com/moby/moby/issues/25303)).
The way around this docker swarm limitation is to create a wrapper service that
runs RQD using docker run. You service wrapper can be defined as:

```Dockerfile
FROM docker

COPY docker_wrapper.sh .

ENTRYPOINT "./docker_wrapper.sh"
```

docker_wrapper.sh
```bash
#!/bin/sh

docker pull RQD_IMAGE

# Ensure the last container got removed, as we're creating named containers
set +e
docker stop -t $STOP_GRACE_SECONDS rqd
docker rm rqd
set -e


# Handle SIGINT and SIGTERM and ask the children container to stop respecting its stop_grace period
handle_exit() {
    echo "Received a request to terminate"
    docker stop -t $STOP_GRACE_SECONDS rqd || true
}
trap 'handle_exit' INT TERM


# Run the rqd container
exec docker run \
 --privileged \
 --rm \
 --name rqd \
 --hostname $(hostname) \
 --pid host \
 --publish mode=host,target=8444,published=8444 \
 --mount type=bind,source=/tmp,target=/tmp,bind-propagation=slave \
 --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock,ro RQD_IMAGE
```

This wrapper does the bare minimum to make your rqd container behave similarly to a docker
swarm service when it comes to reacting to `docker service update` commands. Change it
accordingly if you need to add additional functionalities.