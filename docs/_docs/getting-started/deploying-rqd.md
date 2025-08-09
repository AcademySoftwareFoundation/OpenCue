---
title: "Deploying RQD"
nav_order: 14
parent: Getting Started
layout: default
linkTitle: "Deploying RQD"
date: 2019-02-22
description: >
  Deploy RQD to all OpenCue render hosts
---

# Deploying RQD

### Deploy RQD to all OpenCue render hosts

---

RQD is a software client that runs on all hosts doing work for an OpenCue
deployment.

RQD's responsibilities include:

-   Registering the host with Cuebot.
-   Receiving instructions about what work to do.
-   Monitoring the worker processes it launches and reporting on results.

RQD uses [gRPC](https://grpc.io/) to communicate with Cuebot. It also runs its
own gRPC server, which is called by the Cuebot client to send instructions to
RQD.

## System requirements

Each RQD host must meet the following minimum system requirements:

-   A single physical CPU core
-   2GB RAM

## Before you begin

Before you start to work through this guide, complete the steps in
[Deploying Cuebot](/docs/getting-started/deploying-cuebot).

Make sure you also complete the following steps:

1.  You must provide RQD with the hostname or IP of the Cuebot.

    -   **If you also installed Cuebot in a container**, fetch the container IP:

        ```shell
        export CUEBOT_HOSTNAME=$(docker inspect -f '{{range .NetworkSettings.Networks}}{% raw %}{{.IPAddress}}{% endraw %}{{end}}' cuebot)
        ```

         **If RQD is running locally in your machine in a container**,
    use the Docker API to map the host IP.

        ```shell
        export CUEBOT_HOSTNAME=host.docker.internal
        ```

    -   **If your Cuebot is running on a different machine**, use that machine's
        hostname or IP:

        ```shell
        export CUEBOT_HOSTNAME=<hostname or IP of the Cuebot machine>
        ```

1.  RQD needs access to the filesystem where render assets are stored and log
    files are written. In a large-scale deployment a shared filesystem such as
    NFS is often used for this purpose.

    **If you're running RQD in a Docker container** (Options 1 and 2 below),
    define `CUE_FS_ROOT` and ensure the directory exists:

    ```shell
    export CUE_FS_ROOT="${HOME}/opencue-demo"
    mkdir -p "$CUE_FS_ROOT"
    ```

    **If you're running RQD directly on the host** (Options 3 and 4 below), no
    further action is required. This guide assumes that the filesystem is
    already available on that host. For example, if you plan to run
    [CueGUI](/docs/getting-started/installing-cuegui) and
    [CueSubmit](/docs/getting-started/installing-cuesubmit) on the
    same host, all components can use the local filesystem for this purpose.

1.  On macOS you might also need to
    [increase Docker's RAM limit](https://docs.docker.com/docker-for-mac/#advanced).

### Option 1: Downloading and running RQD from DockerHub

To download and run the pre-built Docker image from DockerHub:

```shell
docker pull opencue/rqd
docker run -td --name rqd01 --env CUEBOT_HOSTNAME=${CUEBOT_HOSTNAME} --volume "${CUE_FS_ROOT}:${CUE_FS_ROOT}" --add-host host.docker.internal:host-gateway opencue/rqd
```

### Option 2: Building and running RQD from source

To build and run the RQD Docker image from source:

```shell
docker build -t opencue/rqd -f rqd/Dockerfile .
docker run -td --name rqd01 --env CUEBOT_HOSTNAME=${CUEBOT_HOSTNAME} --volume "${CUE_FS_ROOT}:${CUE_FS_ROOT}" --add-host host.docker.internal:host-gateway opencue/rqd
```

<!-- -   **In both Option 1 and 2**, if running the RQD container in your local machine, use the `--add-host` flag on the `docker run` command as follows:

    ```shell
    docker run -td --name rqd01 --env CUEBOT_HOSTNAME=${CUEBOT_HOSTNAME} --volume "${CUE_FS_ROOT}:${CUE_FS_ROOT}" --add-host host.docker.internal:host-gateway opencue/rqd
    ``` -->

### Option 3: Installing from pypi

To install from the published pypi release:

You need the `pip` and `virtualenv` tools. Use of a virtual environment is not
strictly necessary but is recommended to avoid conflicts with other installed
Python libraries.

```shell
pip install opencue-rqd
```

An `rqd` executable should now be available in your `PATH`.

This inherits the `CUEBOT_HOSTNAME` environment variable you set earlier in this
guide.

```shell
rqd
```

### Option 4: Installing and running from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

> **Note :** You need the `pip` and `virtualenv`
tools. Use of a virtual environment isn't strictly necessary but is
recommended to avoid conflicts with other installed Python
libraries.>

Ubuntu 22.04 build environment:
```shell
sudo apt install build-essential python3.10-venv python3.10-dev 
```

`rqd` setup:
```shell
virtualenv venv
source venv/bin/activate
pip install rqd/
```

An `rqd` executable should now be available in your `PATH`.

This inherits the `CUEBOT_HOSTNAME` environment variable you set earlier in this
guide.

```shell
rqd
```

## Verifying your install

The following log entries illustrate the expected RQD output, indicating it has
started up:

```
2019-01-31 00:41:51,905 WARNING   rqd3-__main__   RQD Starting Up
2019-01-31 00:41:52,941 WARNING   rqd3-rqcore     RQD Started
```

## Alternative: Rust RQD

OpenCue now offers a high-performance Rust implementation of RQD with improved resource efficiency and experimental features. For more information, see [Rust RQD Reference](/OpenCue/docs/reference/rust-rqd).

## What's next?

*   [Installing PyCue and PyOutline](/docs/getting-started/installing-pycue-and-pyoutline)
*   [Customizing RQD rendering hosts](/docs/other-guides/customizing-rqd)
