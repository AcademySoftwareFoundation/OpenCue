# OpenCue sandbox environment

The sandbox environment offers an easy way to run a test OpenCue deployment locally, with all components running in
separate Docker containers or Python virtual environments. It is ideal for small tests, development work, and for
those new to OpenCue who want a simple setup for experimentation and learning.

To learn how to run the sandbox environment, see
https://www.opencue.io/docs/quick-starts/.

## Usage example

If you don't already have a recent local copy of the OpenCue source code, you must do one of the following:

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
  - CueAdmin is a CLI tool for system administrators managing the render farm infrastructure.

```bash
cueadmin -lh
```

- Verify cueman is working correctly:
  - Cueman is a CLI tool for OpenCue that adds advanced job management and batch control features on top of the OpenCue Python API.
  - For more information see: `cueman/README.md` and `cueman/cueman_tutorial.md`

```bash
cueman -h

# Optional: Run cueman tests to verify installation
cd cueman && python -m pytest tests/ -v
```

- Launch the CueGUI (Cuetopia/CueCommander) app for monitoring and controlling jobs:

```bash
cuegui &
```

- Launch the CueSubmit app for submitting jobs:

```bash
cuesubmit &
```

## Docker Compose Profiles

The main `docker-compose.yml` at the repository root uses profiles to manage optional services:

| Profile | Services |
|---------|----------|
| `default` | cuebot, db, flyway, rqd (always started) |
| `cueweb` | rest-gateway, cueweb |
| `monitoring` | db-exporter, prometheus, grafana, loki |
| `monitoring-full` | zookeeper, kafka, kafka-ui, elasticsearch, kibana, monitoring-indexer |
| `all` | everything |

### Full Stack Deployment

```bash
# From the OpenCue root directory
mkdir -p /tmp/rqd/logs /tmp/rqd/shots

# Core only
docker compose up -d

# Core + Web UI
docker compose --profile cueweb up -d

# Core + Web UI + Monitoring
docker compose --profile cueweb --profile monitoring up -d

# Everything
docker compose --profile all up -d
```

### Access Services

Once deployed, access the services at:

- **CueWeb UI**: http://localhost:3000 (requires `cueweb` profile)
- **REST Gateway**: http://localhost:8448 (requires `cueweb` profile)
- **Cuebot gRPC**: localhost:8443
- **PostgreSQL**: localhost:5432
- **RQD**: localhost:8444
- **Grafana**: http://localhost:3001 (requires `monitoring` profile)
- **Prometheus**: http://localhost:9090 (requires `monitoring` profile)

### Managing Services

```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f cuebot
docker compose logs -f rqd
docker compose logs -f cueweb

# Stop all services (use --profile all to ensure all profiles are stopped)
docker compose --profile all down

# Remove all data volumes
docker compose --profile all down -v
```

### Testing the REST Gateway

To test the REST Gateway API:

**Note:** You need to install `PyJWT` to generate JWT tokens:

```bash
pip install PyJWT
```

**Important:** Do not install `jwt` package - it's a different library and won't work.

```bash
# Get the JWT secret from the running container
export JWT_SECRET=$(docker exec opencue-rest-gateway printenv JWT_SECRET)

# Generate a JWT token
export JWT_TOKEN=$(python3 -c "import jwt, datetime; payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}; print(jwt.encode(payload, '$JWT_SECRET', algorithm='HS256'))")

# Test API access
curl -X POST http://localhost:8448/show.ShowInterface/GetShows \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

For more information on CueWeb and the REST Gateway, see:
- [CueWeb Quick Start](https://www.opencue.io/docs/quick-starts/quick-start-cueweb/)
- [REST Gateway Deployment](https://www.opencue.io/docs/getting-started/deploying-rest-gateway/)
- [REST API Tutorial](https://www.opencue.io/docs/tutorials/rest-api-tutorial/)

## Monitoring

To start monitoring services, use the `monitoring` or `monitoring-full` profile:

```bash
# Basic monitoring (Prometheus, Grafana, Loki)
docker compose --profile monitoring up -d

# Full monitoring with event streaming (adds Kafka, Elasticsearch, Kibana)
docker compose --profile monitoring-full up -d
```

To learn more about monitoring, see https://docs.opencue.io/docs/other-guides/monitoring-with-prometheus-loki-and-grafana/.
