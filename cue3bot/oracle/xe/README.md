
NOTE: This is a stop gap only intended to be used until the postgres swap is ready.


### Initial Setup
To install and run Oracle XE, you'll need to clone the `docker-images` repo from Oracle. You'll also
need to download the Oracle XE rpm from Oracle and copy it into the `docker_setup` folder.
The following commands detail the steps including cleanup. Please note that the `docker_setup` folder is in the
`.gitignore`.

```
mkdir docker_setup
cd docker_setup
git clone https://github.com/oracle/docker-images.git
cp docker-images/OracleDatabase/SingleInstance/dockerfiles/11.2.0.2/* ./
cp ../oracle-xe-11.2.0-1.0.x86_64.rpm.zip ./
rm -rf docker-images
```

### To Build
Oracle requires more shared mem than what Docker is provided by default, make sure to include the "--shm-size" flag.
`docker build --shm-size=1G -t oracle-xe Dockerfile.xe .`

### To Run
Set the password to whatever is the password for the application.
`docker run --shm-size=1G -p 1521:1521 -e ORACLE_PWD=<SET PASSWORD HERE!> oracle-xe`

### To Connect
Oracle SID: `XE`
Port: `1521`
Use `sys as sysdba` user with provided password
Failing to set a password in the docker run command will generate a random password

### Script to build
The above steps can all be accomplished by running the `./run_db_container.sh` script.
It requires two arguments, the system password for the database and a password to create for the cue3 user.

### To Run:
`export PROJECT_ID='YOUR GCP PROJECT ID'`
`./run_db_container.sh <INSERT PASSWORD> <CUE3 DB PASSWORD> [--build-prod]`

### Populating the Schema
Using the `--build-prod` will apply the db schema from `src/main/resources/conf/ddl/db-schema.sql`.
