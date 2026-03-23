---
title: "Monitoring with Prometheus, Loki, and Grafana"
layout: default
parent: Other Guides
nav_order: 52
linkTitle: "Monitoring with Prometheus, Loki, and Grafana"
date: 2021-08-01
description: >
  Configuring OpenCue with external monitoring services
---

# Monitoring with Prometheus, Loki, and Grafana

### Configuring OpenCue with external monitoring services

---

This page describes how to stand up a sample OpenCue deployment configured to send data to external
monitoring services.

The sandbox deployment described here utilizes:

* Prometheus for collecting metrics from the OpenCue database and scheduler.
* Loki for collecting logs from all OpenCue components.
* Grafana to provide an interface for querying and displaying the data send by the others.

## Before you begin

* Follow our [quick start guide](/docs/quick-starts/), which will walk you through standing up a
  basic OpenCue deployment using Docker compose. This guide builds on the quick start, and they
  share the same prerequisites.
* Install the [Loki Docker driver](https://grafana.com/docs/loki/latest/clients/docker-driver/).

## Deploying OpenCue with external monitoring services

You deploy the sandbox environment using
[Docker Compose](https://docs.docker.com/compose/) profiles. The `monitoring` profile runs the following services alongside the core OpenCue stack:

* a PostgreSQL exporter for Prometheus
* a Prometheus instance for metrics storage
* a Loki instance for log storage
* a Grafana instance

To deploy the sandbox environment:

1. If you followed the first quick start before this one, ensure
   [all resources are cleaned up](/docs/quick-starts/quick-start-mac/#stopping-and-deleting-the-sandbox-environment)
   .
2. Start the Terminal app.
3. Change to the root of the OpenCue source code directory:

       cd OpenCue

4. To deploy the sandbox environment with monitoring, run the following command:

       docker compose --profile monitoring up

   The command produces a lot of output. When the setup process completes, you see output similar to
   the following example:

       rqd-1     | WARNING   openrqd-__main__  : RQD Starting Up
       rqd-1     | WARNING   openrqd-rqcore    : RQD Started

Leave this shell running in the background.

## Using Grafana to view exported data

To view the data exported by the monitoring stack, log into the Grafana endpoint provided by the
sandbox environment.

1. Open your browser and visit <http://localhost:3001/>.
2. Log in with the default admin account:
    * User: admin
    * Password: admin
3. Change the `admin` password if prompted.
4. To view the sample dashboards included with the sandbox, click **Dashboards > Manage**.

   ![Manage Grafana dashboards](/assets/images/grafana_manage_dashboards.png)

   Once displayed, these dashboards will show metrics exported from Cuebot and the PostgreSQL database:

   ![Grafana Cuebot metrics](/assets/images/grafana_cuebot_metrics.png)

   ![Grafana PostgreSQL metrics](/assets/images/grafana_cuebot_metrics.png)

## Stopping and deleting the sandbox environment

To delete the resources you created in this guide, run the following commands from the second shell:

1. To stop the sandbox environment, run the following command:

       docker compose --profile all down

2. To also remove all data volumes:

       docker compose --profile all down -v

## What's next?

* Explore Grafana's functionality using the
  [Grafana Getting Started guide](https://grafana.com/docs/grafana/latest/getting-started/).
* Install the full [OpenCue infrastructure](/docs/getting-started/).
