
# OpenCue Sandbox Environment

The sandbox environment provides a way to spin up a test OpenCue deployment that can be used for
running small tests or development. It will run all OpenCue components in separate Docker containers
on your local machine.

The sandbox environment is deployed using docker-compose and will spin up containers for a 
PostgresSQL database, Cuebot, and an RQD instance. docker-compose will also take care of configuring
the database and applying in database migrations. See [https://docs.docker.com/compose/] for more
information on docker-compose. 

A folder will be created for you in the `sandbox` folder called `db-data`. This folder is mounted as
a volume in database container and stores the contents of the database. If you stop your
database container, all data will be preserved as long as you don't remove this folder. If you need
to start from scratch with a fresh database, remove the contents of this folder and restart the 
containers with docker-compose.

1. Once you have docker and docker-compose installed on your machine, run the following steps from
the OpenCue repo root directory to deploy the OpenCue sandbox environment. 

    1. Export an environment variable to specify where to write RQD render logs.
    
            export CUE_FRAME_LOG_DIR=/tmp/rqd/logs
    
    2. Export an environment variable to specify a password for the database (`cuebot` used as an
    example).
    
            export POSTGRES_PASSWORD=cuebot
            
    3. Deploy the sandbox environment with docker-compose.
    
            docker-compose --project-directory . -f sandbox/docker-compose.yml up


2. In a separate shell at the OpenCue root directory we can setup the Python environment to run the
client apps.
    1. Create a virtualenv.
    
            virtualenv venv
    
    2. Source the virtualenv.
    
            source venv/bin/activate
    
    3. Install the Python dependencies to your virtualenv.
    
            pip install -r requirements.txt


3. Now that the sandbox environment is up and your Python environment is good, you'll need to tell
the python apps how to connect to Cuebot. 
    1. The Cuebot docker container is forwarding the gRPC ports to your localhost, so we can connect
     to it as `localhost`. 
    
            export CUEBOT_HOSTS=localhost
            
    2. Launch a new job with CueSubmit.
    
            python cuesubmit/cuesubmit
            
    3. Montior the job with CueGui.
    
            python cuegui/cuegui
            
4. When you're done, stop the environment.
        docker-compose --project-directory . -f sandbox/docker-compose.yml stop

5. Remove the containers to free up space.
        docker-compose --project-directory . -f sandbox/docker-compose.yml rm
