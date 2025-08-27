---
title: "Troubleshooting deployment"
layout: default
parent: Other Guides
nav_order: 32
linkTitle: "Troubleshooting deployment"
date: 2019-02-22
description: >
  Troubleshoot common deployment issues
---

# Troubleshooting Deployment

### Troubleshoot common deployment issues

---

This page describes common issues you might encounter while deploying OpenCue
and how to debug them.

## Checking Cuebot logs

When using OpenCue client-side software such as CueGUI or CueSubmit you might
encounter unknown errors, such as the following, which require you to view the
Cuebot logs for more detail:

```
opencue.exception.CueException: Encountered a server error. StatusCode.UNKNOWN : No details found. Check server logs.
```

To troubleshoot this type of error message:

1.  Log into the machine on which Cuebot is running. If Cuebot is running in a
    Docker container, you must open a shell in that container.

    ```shell
    export CUEBOT_CONTAINER=<the name of your Cuebot container>
    docker exec -it $CUEBOT_CONTAINER bash
    ```

1.  The main Cuebot log file is located at `logs/spcue.log`. Use your editor or
    other tool of choice to view that file:

    ```shell
    tail -n 50 logs/spcue.log
    ```

The logs provide information that can help indicate what went wrong, such as
stacktraces and other more detailed error messages.

## Connecting from Cuebot to the database

If Cuebot has a problem connecting to its database, you might see error messages
like the following in the Cuebot logs:

```
org.postgresql.util.PSQLException: The connection attempt failed.
```

To troubleshoot this type of error message:

1.  **Make sure your PostgreSQL server is up and the PostgreSQL service is
    running.** The verification process differs depending on
    [how you deployed your PostgreSQL server](/docs/getting-started/setting-up-the-database).

1.  **Test networking from Cuebot.** Make sure that your networking is
    configured as intended by running a network test without PostgreSQL. You can
    run tests such as the following using `telnet`:

    ```shell
    export DB_HOST=<your database IP or hostname>
    export DB_PORT=<your database port, default is 5432>
    telnet $DB_HOST $DB_PORT
    ```

    The expected response is a `Connected` message.

    ```
    Trying <database IP>...
    Connected to <database IP>.
    Escape character is '^]'.
    ```

    If you don't, and telnet hangs or times out trying to connect, the problem
    is likely at the networking level, and the Cuebot host isn't able to reach
    the database server at all.

1.  **Test connecting to the database using the psql client.** Use the
    PostgreSQL client `psql` to test whether you can initiate a PostgreSQL
    shell, as follows:

    ```shell
    export DB_HOST=<your database IP or hostname>
    export DB_USER=cuebot
    export DB_NAME=cuebot
    psql -h $DB_HOST -U $DB_USER $DB_NAME
    ```

    The expected response is a prompt for your user's PostgreSQL password. Enter
    the password then connect to the PostgreSQL command prompt:

    ```
    Password for user postgres:
    SSL connection (cipher: ECDHE-RSA-AES128-GCM-SHA256, bits: 128)
    Type "help" for help.

    cuebot=>
    ```

    If the connection fails, the PostgreSQL error typically provides more detail
    about why it failed, such as the following common problems:

    -   Database does not exist - database creation failed or was skipped.
    -   Authentication failed - the database user doesn't exist, or an incorrect
        password was supplied.

1.  **Run a query using the psql client.** After following the previous step,
    run a SQL query directly:

    ```shell
    cuebot=> SELECT str_name FROM show;
    ```

    The expected response is a table printout of any shows in your database. The
    exact results can vary depending on the contents of your database.

    ```
     str_name
    ----------
     testing
    (1 row)
    ```

    Common problems are:

    -   `relation "show" does not exist` - this might mean:
        -   The database table doesn't exist. For example the population of the
            database schema might have failed or been skipped.
        -   The database user doesn't have access to that table. For example the
            user might not have been properly granted access to the database.

1.  **Check your Cuebot configuration.** Database parameters are passed to the
    Cuebot via command-line args to the Cuebot JAR file. Depending on your
    deployment method this might be passed multiple ways. For more details, see
    [Deploying Cuebot](/docs/getting-started/deploying-cuebot).

    Make sure that Cuebot is configured to use the same database parameters you
    used in the rest of these debugging steps, such as hostname, user, and
    password.

## Connections between Cuebot and RQD

If RQD is unable to reach the Cuebot, RQD might throw gRPC error messages like
the following:

```
grpc._channel._Rendezvous: <_Rendezvous of RPC that terminated with:
    status = StatusCode.UNAVAILABLE
    details = "Connect Failed"
  ...
```

To troubleshoot this type of error message:

1.  **Make sure your Cuebot server is up and that the Cuebot software is
    running.** The process here differs depending on
    [how you deployed your Cuebot server](/docs/getting-started/deploying-cuebot).
    If you deployed Cuebot within a Docker container, make sure the container is
    running and healthy.

1.  **Test networking from RQD.** Make sure that your networking is configured
    as intended by running a network test between the RQD host and the Cuebot
    host. You can run tests such as the following using `telnet`:

    ```shell
    export CUEBOT_HOST=<your Cuebot server IP or hostname>
    telnet $CUEBOT_HOST 8443
    ```

    The expected response is a `Connected` message:

    ```
    Trying <Cuebot IP>...
    Connected to <Cuebot IP>.
    Escape character is '^]'.
    ```

    If you don't, and telnet hangs or times out trying to connect, the problem
    is likely at the networking level, and the RQD host isn't able to reach the
    Cuebot server at all.

1.  **Check the RQD environment.** RQD uses the `CUEBOT_HOSTNAME` environment
    variable to determine which Cuebot server to connect to. The method of
    checking this depends on
    [how you deployed your RQD hosts](/docs/getting-started/deploying-rqd).

    For example, if you deployed RQD in a Docker container, you can inspect the
    container:

    ```shell
    docker inspect <RQD container name> | grep CUEBOT_HOSTNAME
    ```

    Ensure the hostname is defined in the container configuration:

    ```
                "CUEBOT_HOSTNAME=<Cuebot hostname or IP address>",
    ```

    Make sure that the value stored in `CUEBOT_HOSTNAME` matches what you've
    been using in the previous steps.
