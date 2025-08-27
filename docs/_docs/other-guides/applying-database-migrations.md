---
title: "Applying database migrations"
layout: default
parent: Other Guides
nav_order: 31
linkTitle: "Applying database migrations"
date: 2019-08-22
description: >
  Apply new database migrations
---

# Applying Database Migrations

### Apply new database migrations

---

This page describes how to apply new database migrations when necessary. This
guide is intended for OpenCue system admins.

Occasionally changes in OpenCue also require an update to the database schema.
When this happens, the development team add the schema changes as a new
*migration*. The migration contains raw SQL and only includes the parts of
the schema that have changed. You can apply and safely roll back the migration
using the database management tool of your choice. This guide describes how to
apply the migration using [flyway](https://flywaydb.org/).

When you update Cuebot, you must also apply any new migrations to ensure the
Cuebot code matches the correct database schema. Changes that require a
database migration are noted in the
[OpenCue release notes](https://www.opencue.io/blog/releases/).

## Applying a migration

To apply a migration:

1.  Stop Cuebot, by either killing the Cuebot process or stopping its
    container.

1.  To execute the migrations, you run the `flyway` command and supply the
    credentials from the original
    [database installation](/docs/getting-started/setting-up-the-database).
    Run the `flyway` from the root folder of the OpenCue repo:

    ```shell
    flyway -url=jdbc:postgresql://$DB_HOST/$DB_NAME -user=$USER -n -locations=filesystem:cuebot/src/main/resources/conf/ddl/postgres/migrations migrate
    ``` 

1.  To update Cuebot to the version that corresponds to the database changes,
    follow the installation instructions in
    [Deploying Cuebot](/docs/getting-started/deploying-cuebot).

1.  Restart Cuebot.

## What's next?

*   To stay up to date on changes that might require database migrations,
    subscribe to the RSS feed for the
    [OpenCue release notes](https://www.opencue.io/blog/releases/).
