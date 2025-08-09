---
title: "Deploying Cuebot"
nav_order: 13
parent: Getting Started
layout: default
linkTitle: "Deploying Cuebot"
date: 2019-02-22
description: >
  Deploy Cuebot to a server from source or a Docker image
---

# Deploying Cuebot

### Deploy Cuebot to a server from source or a Docker image

---

This guide shows you how to build a Docker image to run Cuebot.


Cuebot typically runs on a server and performs a variety of important OpenCue
management tasks, including:

*   Managing OpenCue jobs and job submissions.
*   Distributing work to render nodes.
*   Responding to API requests from client-side tools such as CueGUI.

A typical OpenCue deployment runs a single instance of Cuebot, which is shared
by all users.


## System requirements

To plan your installation of Cuebot, consider the following requirements:

*   A Cuebot server requires a minimum of 6GB of RAM.
*   Cuebot functions best when it has a low-latency connection to the
    [OpenCue database](/docs/getting-started/setting-up-the-database). We recommend that you
    run Cuebot either on the same machine or within the same local network as the database.

## Before you begin

Before you work through the steps in this guide, make sure you complete the
steps in
[Setting up the database](/docs/getting-started/setting-up-the-database).

A Cuebot server requires a minimum of 6GB of memory.

Make sure you also complete the following steps:

1.  Configure database values. Use the same values you used in
    [Setting up the database](/docs/getting-started/setting-up-the-database).

    ```shell
    export DB_NAME=cuebot_local
    export DB_USER=cuebot
    export DB_PASS=<changeme>
    ```

1.  If you plan to run Cuebot in a Docker container (Options #1 and #2 below)
    you must also install [Docker](https://www.docker.com/). For installation
    instructions for your platform, see
    [the Docker docs](https://docs.docker.com/install/).

1.  If you plan to run Cuebot in a Docker container, you must also define the
    environment variable `DB_HOST_IN_DOCKER`.

    -   **If you also installed PostgreSQL in a container**, fetch the IP
        address for the PostgreSQL container:

        ```shell
        export DB_HOST_IN_DOCKER=$(docker inspect -f '{{range .NetworkSettings.Networks}}{% raw %}{{.IPAddress}}{% endraw %}{{end}}' <name of Postgres container>)
        ```

    -   **If you are running Docker for macOS and your database is running on
        the macOS host**, specify `host.docker.internal`:

        ```shell
        export DB_HOST_IN_DOCKER=host.docker.internal
        ```

    -   **If your database is running on a different machine**, specify the IP
        address of the host for your database:

        ```shell
        export DB_HOST_IN_DOCKER=<IP address of the database host machine>
        ```

    > **Note**
> {: .callout .callout-info}If you are running Docker on Linux
    and your database is running directly on the host machine, you will likely
    need to start your Cuebot container with `--net=host` in order to connect
    to the database. This configuration is outside of the scope of this
    guide.>

1.  Cuebot needs to know the location of the filesystem where render assets
    are stored and log files are written. In a large-scale deployment a shared
    filesystem such as NFS is often used for this purpose. For the purposes of
    this guide, you can use any directory you have write access to.

    ```shell
    export CUE_FS_ROOT="$HOME/opencue-demo"
    mkdir -p "$CUE_FS_ROOT"
    ```

    If you plan to run [CueGUI](/docs/getting-started/installing-cuegui) and
    [CueSubmit](/docs/getting-started/installing-cuesubmit) on the same host
    as Cuebot, then all three components can use the local filesystem on that
    host.

## Installing and running Cuebot

### Option 1: Download and run the pre-built Docker image from DockerHub

To download and run the Cuebot Docker image:

1.  Download the Docker image from Docker hub:

    ```shell
    docker pull opencue/cuebot
    ```

1.  To start Cuebot, run the Docker image:

    ```shell
    docker run -td --name cuebot -p 8080:8080 -p 8443:8443 opencue/cuebot --datasource.cue-data-source.jdbc-url=jdbc:postgresql://$DB_HOST_IN_DOCKER/$DB_NAME --datasource.cue-data-source.username=$DB_USER --datasource.cue-data-source.password=$DB_PASS  --log.frame-log-root.default_os="${CUE_FS_ROOT}/logs"
    ```

### Option 2: Build and run the Cuebot Docker image from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

To build and run the Cuebot Docker image:

1.  Build the Docker image and tag it as `opencue/cuebot`:

    ```shell
    docker build -t opencue/cuebot -f cuebot/Dockerfile .
    ```

1.  To start Cuebot, run the Docker image:

    ```shell
    docker run -td --name cuebot -p 8080:8080 -p 8443:8443 opencue/cuebot --datasource.cue-data-source.jdbc-url=jdbc:postgresql://$DB_HOST_IN_DOCKER/$DB_NAME --datasource.cue-data-source.username=$DB_USER --datasource.cue-data-source.password=$DB_PASS --log.frame-log-root.default_os="${CUE_FS_ROOT}/logs"
    ```

### Option 3: Manually install from the published release

Visit https://github.com/AcademySoftwareFoundation/OpenCue/releases and download the cuebot JAR
from the latest release's Assets.

1.  You must have a Java Runtime Environment (JRE) installed with which to run
    the JAR file. Java 8+ is supported for OpenCue.

    On CentOS this can be installed using `yum`:

    ```shell
    sudo yum install java-1.8.0-openjdk
    ```

    On macOS you can use Homebrew:

    ```shell
    brew tap caskroom/versions
    brew cask install java8
    ```

1.  Next, use your JRE to run the Cuebot JAR file:

    ```shell
    export JAR_PATH=<path to Cuebot JAR>
    java -jar $JAR_PATH --datasource.cue-data-source.jdbc-url=jdbc:postgresql://$DB_HOST/$DB_NAME --datasource.cue-data-source.username=$DB_USER --datasource.cue-data-source.password=$DB_PASS --log.frame-log-root.default_os="${CUE_FS_ROOT}/logs"
    ```

### Option 4: Build from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

1.  You must have a Java Runtime Environment (JRE) installed with which to run
    the JAR file. Java 8+ is supported for OpenCue.

    On CentOS this can be installed using `yum`:

    ```shell
    sudo yum install java-1.8.0-openjdk java-1.8.0-openjdk-devel
    ```
    On Ubuntu 22.04:
    ```shell
    sudo apt install openjdk-11-jdk-headless
    ```

    On macOS you can use Homebrew:

    ```shell
    brew tap caskroom/versions
    brew cask install java8
    ```

1.  Next, use Gradle to build the Cuebot JAR file from source. The OpenCue
    source code comes packaged with a Gradle executable for this purpose:

    ```shell
    cd cuebot
    ./gradlew build
    ```

1.  Finally, use your JRE to run the Cuebot JAR:

    ```shell
    java -jar build/libs/cuebot.jar --datasource.cue-data-source.jdbc-url=jdbc:postgresql://$DB_HOST/$DB_NAME --datasource.cue-data-source.username=$DB_USER --datasource.cue-data-source.password=$DB_PASS --log.frame-log-root.default_os="${CUE_FS_ROOT}/logs"
    ```

## Verifying your install

Cuebot produces a startup screen at launch:

```

  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/
 :: Spring Boot ::

```
To view the startup screen:

1.  If you're running Cuebot in a Docker container, run the following command:

    ```shell
    docker logs cuebot
    ```

1.  If you're running the Cuebot JAR directly in the native operating system of
    your machine, you can view the startup screen in the output of the terminal
    you used to start the JAR.

## What's next?

*   [Deploying RQD](/docs/getting-started/deploying-rqd)
