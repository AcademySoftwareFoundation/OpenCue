# OpenCue sandbox environment

The sandbox environment provides a way to run a test OpenCue deployment. You
can use the test deployment to run small tests or development work. The sandbox
environment runs OpenCue components in separate Docker containers on your local
machine.

## Before you begin

You must have the following software installed on your machine:

*   [Docker](https://docs.docker.com/install/)
*   [Docker Compose](https://docs.docker.com/compose/install/)
*   Python version 2.7 or greater
*   The Python [`pip` command](https://pypi.org/project/pip/)
*   The Python [virtualenv tool](https://pypi.org/project/virtualenv/)

You must allocate a minimum of 6 GB of memory to Docker. To learn
how to update the memory limit on macOS, see
[Get started with Docker Desktop for Mac](https://docs.docker.com/docker-for-mac/#advanced).

If you don't already have a local copy of the OpenCue source code, you must do
one of the following:

1.  Download and unzip the
    [OpenCue source code ZIP file](https://github.com/AcademySoftwareFoundation/OpenCue/archive/master.zip).
2.  If you have the `git` command installed on your mahine, you can clone
    the repository:

        git clone https://github.com/AcademySoftwareFoundation/OpenCue.git

## Deploying the OpenCue sandbox environment

The sandbox environment is deployed using
[Docker Compose]([https://docs.docker.com/compose/]) and runs the following
containers:

*   a PostgresSQL database
*   a Cuebot server
*   an RQD instance.

The Docker Compose deployment process also configures the database and applies
any database migrations. The deployment process also creates a `db-data`
directory in the `sandbox` directory called . The `db-data` directory is
mounted as a volume in the PostgresSQL database container and stores the
contents of the database. If you stop your database container, all data is
preserved as long as you don't remove this directory. If you need to start
from scratch with a fresh database, remove the contents of this directory and
restart the containers with the `docker-compose` command.

To deploy the OpenCue sandbox environment:

1.  Change to the root of the OpenCue source code directory:

        cd OpenCue

2.  To deploy the OpenCue sandbox environment, export the `CUE_FRAME_LOG_DIR`
    environment variable:

        export CUE_FRAME_LOG_DIR=/tmp/rqd/logs

3.  To specify a password for the database, export the `POSTGRES_PASSWORD`
    environment variable:

        export POSTGRES_PASSWORD=<REPLACE-WITH-A-PASSWORD>

4.  To deploy the sandbox environment, run the `docker-compose` command:

        docker-compose --project-directory . -f sandbox/docker-compose.yml up

Leave this shell running in the background.

## Installing the OpenCue client packages

OpenCue includes the following client packages to help you submit,
monitor, and manage rendering jobs:

*   PyCue is the OpenCue Python API. OpenCue client-side Python tools, such as
    CueGUI and `cueadmin`, all use PyCue for communicating with your OpenCue
	deployment.
*   PyOutline is a Python library, that provides a Python interface to the
    job specification XML, allowing you to construct complex jobs with Python
	code instead of working directly with XML. 
*   CueSubmit is a graphical user interface for configuring and launching
    rendering jobs to an OpenCue deployment.
*   CueGUI is a graphical user interface you run to monitor and manage jobs,
    layers, and frames.
*   `cueadmin` is the OpenCue command-line client for administering an OpenCue
    deployment.
*   `pycuerun` is a command-line client for submitting jobs to OpenCue.

To install the OpenCue client packages


1.  Open a second shell.

1.  Change to the root of the OpenCue source code directory:

        cd OpenCue

1.  Create a virtual environment for the Python packages:

        virtualenv venv

2.  Activate the `venv` virtual environment:

        source venv/bin/activate

3.  Install the Python dependencies and client packages in the `venv` virtual
    environment:

        sandbox/install-clients.sh

## Test the sandbox environment

To connect to the sandbox environment, you must configure your local client
packages to connect to Cuebot.

Run the following commands from the second shell:

1.  Set the location of the PyOutline configuration file:

        export OL_CONFIG=pyoutline/etc/outline.cfg

2.  The Cuebot docker container is forwarding the gRPC ports to your
    localhost, so you can connect to it as `localhost`: 
    
        export CUEBOT_HOSTS=localhost

3.  To list the hosts in the sandbox environment, run the `cueadmin`
    command:

        cueadmin -lh

4.  Launch a new job with CueSubmit:

        cuesubmit &

5.  Montior the job with CueGUI:

        cuegui &

## Stop and delete the sandbox environment

To delete the resources you created in this guide, run the following commands
from the second shell:

1.  To stop the sandbox environment, run the following command:

        docker-compose --project-directory . -f sandbox/docker-compose.yml stop

2.  To free up storage space, delete the containers:

        docker-compose --project-directory . -f sandbox/docker-compose.yml rm

3.  To delete the virtual environment for the Python client packages:

        rm -rf venv

## What's next?

*   Learn more about [OpenCue concepts and terminology](https://www.opencue.io/docs/concepts/).
*   Install the full [OpenCue infrastructure](https://www.opencue.io/docs/getting-started/).
