# OpenCue sandbox environment

The sandbox environment offers an easy way to run a test OpenCue deployment locally, with all components running in 
separate Docker containers or Python virtual environments. It is ideal for small tests, development work, and for 
those new to OpenCue who want a simple setup for experimentation and learning.

To learn how to run the sandbox environment, see
https://www.opencue.io/docs/quick-starts/.

## Usage example

If you don’t already have a recent local copy of the OpenCue source code, you must do one of the following:

- Download and unzip the [OpenCue source code ZIP file](https://github.com/AcademySoftwareFoundation/OpenCue/archive/master.zip).
- If you have the git command installed on your machine, you can clone the repository:

```bash
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
```

For developers, you can also use the following commands to set up a local copy of the OpenCue source code:

- Fork the [Opencue repository](https://github.com/AcademySoftwareFoundation/OpenCue) using your GitHub account.
- Clone your forked repository:
```bash
git clone https://github.com/<username>/OpenCue.git
```

### 1. Deploying the OpenCue Sandbox Environment

- Run the services: DB, Flyway, Cuebot, and RQD
  - A PostgreSQL database
  - A Flyway database migration tool
  - A Cuebot server
  - An RQD rendering server

In one terminal, run the following commands:

- Create required directories for RQD logs and shots:

```bash
mkdir -p /tmp/rqd/logs /tmp/rqd/shots
```

- Change to the root of the OpenCue source code directory

```bash
cd OpenCue
```

- Build the Cuebot container from source

**Note:** Make sure [Docker](https://www.docker.com/) is installed and running on your machine.

```bash
docker build -t opencue/cuebot -f cuebot/Dockerfile .
```

- Deploy the sandbox environment
  - This command will start the services (db, flyway, cuebot, rqd) in the background and create a network for them to 
  communicate with each other.

```bash
docker compose up
```

**Notes:** 
- Use `docker compose up -d` to run the services in detached mode.
- Use `docker compose down` to stop the services and remove the network.
- Use `docker compose logs` to view the logs of the services.
- Use `docker compose ps` to view the status of the services.
- Use `docker compose exec <service> bash` to open a shell in the container of the specified service.
- Use `docker compose exec <service> <command>` to run a command in the container of the specified service.
- Use `docker compose down --volumes` to remove the volumes created by the services.
- Use `docker compose down --rmi all` to remove all images created by the services. 

### 2. Installing the OpenCue Client Packages

In a second terminal, run the following commands:

- Make sure you are in the root of the OpenCue source code directory

```bash
cd OpenCue
```

- Create a virtual environment for the Python packages

```bash
python3 -m venv sandbox-venv
```

- Activate the virtual environment

```bash
source sandbox-venv/bin/activate
```

- Upgrade pip to the latest version

```bash
pip install --upgrade pip
```

- Install the required Python packages

```bash
pip install -r requirements.txt
pip install -r requirements_gui.txt
```

- Install the OpenCue Python client libraries from source
  - This option is mostly used by developers that contribute to the OpenCue project.
  - It is recommended if you want to test the latest changes in the OpenCue source code.
  - To install Opencue from source, run:

```bash
./sandbox/install-client-sources.sh
```

**Note:** The latest version of the OpenCue source code might include changes that are incompatible with the prebuilt 
OpenCue images of Cuebot and RQD on Docker Hub used in the sandbox environment.

Alternatively, you can use the script `./sandbox/install-client-archive.sh` to download, extract, and install specified 
OpenCue client packages for a given release version from GitHub. To learn how to run the sandbox environment, see
https://www.opencue.io/docs/quick-starts/.
- To install the latest versions of the OpenCue client packages, you must configure the installation script with the 
version number. 
- The script `sandbox/get-latest-release-tag.sh` will automatically fetch this for you, but you can also look up the 
version numbers for OpenCue releases on GitHub.

```bash
export VERSION=$(sandbox/get-latest-release-tag.sh)
``` 

### 3. Testing the Sandbox Environment

To test the sandbox environment, run the following commands inside the Python virtual environment:

- To verify the successful installation and connection between the client packages and sandbox, list the hosts in the 
sandbox environment:

```bash
cueadmin -lh
```

- Launch the CueGUI (Cuetopia/CueCommander) app for monitoring and controlling jobs:

```bash
cuegui &
```

- Launch the CueSubmit app for submitting jobs:

```bash
cuesubmit &
```

## Monitoring

To get started with monitoring there is also an additional Docker compose file which sets up
monitoring for key services.

To learn how to run the sandbox environment with monitoring,
see https://www.opencue.io/docs/other-guides/monitoring-with-prometheus-loki-and-grafana/.