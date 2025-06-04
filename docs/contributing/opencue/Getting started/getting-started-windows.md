---
title: "Setting up a development environment on Windows"
linkTitle: "Setting up a development environment on Windows"
date: 2020-01-29
weight: 1
description: >
  Set up your development environment on Windows
---

This is a guide to setting up a development environment on Windows that lets
you run the entire OpenCue system, including Cuebot, CueGUI, and RQD. After
you complete the setup, you can make changes to any part of the development
environment.

## Before you begin

First, clone the
[OpenCue git repository](https://github.com/AcademySoftwareFoundation/OpenCue)
to your machine. You also need to download and install three core dependencies:

- [PostgreSQL](https://www.postgresql.org/download/windows/) version 9 or
  greater
- [Python 3.x](https://www.python.org/downloads/) 
- [Java SE JDK](https://www.oracle.com/technetwork/java/javase/downloads/index.html)
  version 11 or greater

It's also useful to install an IDEs. JetBrains has free community versions of
the following options:

- [PyCharm](https://www.jetbrains.com/pycharm/) for Python
- [IntelliJ IDEA](https://www.jetbrains.com/idea/) for Java

## Database setup

After installing PostgreSQL you need to create a database and user for OpenCue
(specifically Cuebot) to use.

To do this you can either use the pgAdmin GUI, which is included with
PostgreSQL on Windows, or the command-line PostgreSQL client.

### Using the command-line

To set up the database using the command-line:

1. Download the `schema-*.sql` and `seed_data-*.sql` files from the
[the releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases).
   
{{% alert title="Note" color="info"%}}In older releases `seed_data.sql` is called `demo_data.sql`.{{% /alert %}}

1. Open Powershell, then run `psql`:

    ```powershell
    # Change the following path depending on what version of PostgreSQL you have:
    $psql = 'C:\Program Files\PostgreSQL\12\bin\psql.exe'
    & $psql -U postgres
    ```

1. Enter the password you set during PostgreSQL installation.

1. Next, enter the following `psql` commands to set up the user and database:

```psql
create user opencue with password 'INSERT PASSWORD HERE';
create database opencue;
\connect opencue
alter default privileges in schema public grant all privileges on tables to opencue;
\include schema-*.sql # actual filename changes depending on version
set search_path = public;
\include seed_data-*.sql # actual filename changes depending on version
\quit
```

### Using the pgAdmin GUI

To set up the database using the pgAdmin GUI:

1. To start pgAdmin, open pgAdmin from the Start menu.

   This adds an icon to the system tray.

1. Right-click the pgAdmin icon and click **New pgAdmin window…**,
   which will open  in your browser.

1. Sign in with your PostgreSQL admin user credentials that you selected during
   the PostgreSQL installation.

1. To create a user, from the tree-view on the left, right-click
   **Login/Group Roles** and select **Create→Login/Group Role…**.

1. Name the user `opencue` and choose a secure password, then click **Save**.

1. To create a database, from the tree-view on the left, right-click
   **Databases** and select **Create** > **Database…**.
   
1. Name the database `opencue`, then click **Save**.

   Next you need to populate the database.

1. To populate the database, as described in the instructions on the
   [Setting up the Database](/docs/getting-started/setting-up-the-database/) 
   page to populate the database, you can:
   
   1. Download the latest `schema-*.sql` from
      [the releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases).
   
   1. In pgAdmin right-click the `opencue` database, and select **Query Tool…**.
   
   1. In the Query Editor click 📂 (Open File icon) and open the `.sql` file you
      downloaded.
   
   1. Click ▶ (Execute icon) to populate the database.

   You also need the demo data to run the full environment locally.

1. To insert demo data, download the latest `seed_data-*.sql` from the
   [releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases)
   and run it against the `opencue` database as described in the previous step.
   
   {{% alert title="Note" color="info"%}}In older releases `seed_data.sql` is called `demo_data.sql`.{{% /alert %}}

1. To grant permissions, in pgAdmin, right-click on the `opencue` database and
   select **Grant Wizard**.

1. Use the select-all box to select all items, then select **Next**.

1. Add the `opencue` user and select `ALL` privileges, then select **Next**
   again, and then click **Finish**.

## Configure PyCue for local CueBot server

You need to change the default servers for the `opencue` Python library, so
that it can find your local Cuebot server.

Open `pycue/opencue/default.yaml`, and edit the end of the file to look like
the following:

```yaml
cuebot.facility_default: local
cuebot.facility:
  local:
  - localhost:8443
```

## Generate gRPC .proto files

Generating the `.proto` gRPC protocol files for RQD and the PyCue library is
currently a manual process. To generate the `.proto` files:

1. Open Powershell and install the required gRPC tools:

    ```powershell
    pip install grpcio-tools
    ```

1. Change directory to the `proto` folder.

1. Run the following commands (from `proto/README.md`):

    ```powershell
    python -m grpc_tools.protoc --proto_path=. --python_out=../rqd/rqd/compiled_proto --grpc_python_out=../rqd/rqd/compiled_proto (ls *.proto).Name
    python -m grpc_tools.protoc --proto_path=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto (ls *.proto).Name
    ```

    The `.proto` files also need some post-processing to make them compatible
    with Python 3. The easiest way to do this is to install and run the `2to3`
    package.

1. Run the following commands to install the `2to3` package and complete the
post-processing:

    ```powershell
    pip install 2to3
    2to3 -wn (ls ../rqd/rqd/compiled_proto/*_pb2*)
    2to3 -wn (ls ../pycue/opencue/compiled_proto/*_pb2*)
    ```

## Running Cuebot

Cuebot is the core component of OpenCue, written in Java.

To build and run it with IntelliJ IDEA:

1. Open IntelliJ IDEA and choose **Open**, select the `cuebot` folder in the git repository.
   
   The IDE downloads and sets up Gradle, if required, which can take some time.

1. Browse to the `src/main/java/com.imageworks/spcue/CuebotApplication` file.

1. Click **Edit 'CubotApplicat....main()'...**.

1. Update the **Program arguments** as follows and replace the value for `<PASSWORD>`
   where indicated:

   ```
   --datasource.cue-data-source.jdbc-url=jdbc:postgresql://localhost/opencue --datasource.cue-data-source.username=opencue --datasource.cue-data-source.password=<PASSWORD>
   ```
 
1. Click **OK**.
 
1. Click **Run** > **Run 'CuebotApplication'**.

1. Verify that the output window doesn’t show any errors.

   If it does, double-check that you have set up the database correctly,
   including permissions, and have set the Program arguments correctly.

## Running CueSubmit

CueSubmit lets you submit jobs to OpenCue, written in Python.

To set up CueSubmit and run it with PyCharm:

1. Open PyCharm and choose **Open**, select the `cuesubmit` folder in the git
   repository.

1. For the project interpreter, if you are working on other Python projects, we
   recommend setting up a virtual environment. Alternatively, you can leave the
   project interpreter set to the default Python interpreter.

1. PyCharm should prompt you to install ‘Package requirements’. If not,
   open the `setup.py` and the banner should appear.
   
1. Select **Install Requirements** and wait for the packages to be installed.

   PySide2 can take some time to install.

1. You need to add additional content roots to find the `opencue` and
   `outline` libraries. Under **File** > **Settings**, find
   **Project: cuesubmit/Project Structure**, then click ➕ (plus icon) next to
   **Add Content Root** and add the `pycue` folder.
   
1. Repeat the previous step for the `pyoutline` folder.

1. Select **OK** to exit.

1. Right-click `cuesubmit/__main__.py` and click **Run**.

## Running CueGUI

CueGUI lets you monitor the status of jobs and rendering hosts. It is written in Python.

To set up CueGUI and run it with PyCharm:

1. Open PyCharm and click **Open**.

1. Select the `cuegui` folder in the git repository.

1. For the project interpreter, if you are working on other Python projects, we
   recommend setting up a virtual environment. Alternatively, you can leave the
   project interpreter set to the default Python interpreter.

1. PyCharm should prompt you to install ‘Package requirements’. If not,
   open the `setup.py` and the banner should appear.
   
1. Select **Install Requirements** and wait for the packages to be installed.

   PySide2 can take some time to install.

1. You need to add additional content roots to find the `opencue` library.
   Under **File** > **Settings**, find **Project: cuegui/Project Structure**,
   then click the ➕ (plus icon) next to **Add Content Root** and add the `pycue`
   folder.

1. Select **OK** to exit.

1. Right-click `cuegui/__main__.py` and click **Run**.

## Running RQD

RQD is the OpenCue rendering host agent. It is written in Python.

To get set up and run it with PyCharm:

1. Open PyCharm and choose **Open**, select the `rqd` folder in the git repository.

1. For the project interpreter, if you are working on other Python projects, we
   recommend setting up a virtual environment. Alternatively, you can leave the
   project interpreter set to the default Python interpreter.

1. PyCharm should prompt you to install ‘Package requirements’. If not,
   open the `setup.py` and the banner should appear.

1. Select **Install Requirements** and wait for the packages to be installed.

1. Right-click `rqd/__main__.py` and click **Run**.

## Verify your installation

After you are running CueBot, CueGUI, and RQD simultaneously, you should be
able to see the RQD host in CueGUI:

1. From the **Views/Plugins** menu, click **Cuecommander** > **Monitor Hosts**.

1. In the **Monitor Hosts** section, check the **Auto-refresh** box as
illustrated by the following screenshot:

   ![A screenshot of CueGUI showing host](/docs/images/windows/verify_host.png)

    Next, check that you can run a job by using CueSubmit.

1. Switch to CueSubmit and fill out Job, Shot, and Layer Name fields as
   you like.

1. Set the Command to `ping opencue.io`.

1. Set Frame Spec to `1`.

1. Click **Submit**:

   ![A screenshot of CueSubmit with correct values](/docs/images/windows/verify_submit.png)

1. Switch back to CueGUI and verify that the job completes successfully:

   ![A screenshot of CueGUI with completed job](/docs/images/windows/verify_job_complete.png)

This verifies that your end-to-end installation is working.
