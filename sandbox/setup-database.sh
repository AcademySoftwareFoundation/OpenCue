#!/bin/bash

# Script to setup the database

###
# Disclaimer: This is currently experimental and isn't recommended for general use yet.
###

GREEN="\033[1;32m"
NC="\033[0m"

IS_DOCKER=0
BASE_URL=https://github.com/AcademySoftwareFoundation/OpenCue/releases/download/

if [[ -z "${VERSION}" ]]; then
    echo "You must set the release version number. For example:"
    echo "export VERSION=0.2.31"
    echo "For a list of OpenCue version numbers, visit the following URL:"
    echo "https://github.com/AcademySoftwareFoundation/OpenCue/releases/"
    exit 1
fi

set -e

echo ""
echo "Setting up database..."
echo ""
echo "Installing Postgres"
echo ""
echo "OPTION 1: Install on Docker"
echo "OPTION 2: Install on Linux"
echo "OPTION 3: Install on MacOS"
echo ""

read -n 1 -p "Select mode of installation: " VAR

if [[ $VAR -eq 1 ]]
then
    echo ""
    echo ""
    echo -e "${GREEN}Installing on Docker...${NC}"
    IS_DOCKER=1

    # Pulling the Postgres image from Docker hub 
    docker pull postgres 

    # Starting the Postgres container:
    echo ""
    read -p "What would you like to name your Postgres container: " PG_CONTAINER_INPUT
    export PG_CONTAINER=$PG_CONTAINER_INPUT

    # Creating a superuser named after the current OS user
    docker run -e POSTGRES_HOST_AUTH_METHOD=trust -td --name "$PG_CONTAINER" postgres 
    sleep 2
    docker exec -it --user=postgres "$PG_CONTAINER" createuser -s "$USER"

    echo ""
    read -n 1 -p "Would you like to install a Postgres client? (Y/n): " PG_CLIENT_OPT

    if [[ $PG_CLIENT_OPT = "Y" ]] || [[ $PG_CLIENT_OPT = "y" ]]
    then
        echo ""
        echo ""
        echo -e "${GREEN}Installing Postgres Client...${NC}"
        if [[ $(uname) = "Darwin" ]] # Client for macOS
        then
            brew install postgresql
        elif [[ $(uname) = "linux-gnu" ]] # Client for linux-gnu
        then
            yum install postgresql-contrib
        else
            echo ""
            echo "Your Operating System may not support a Postgres client yet!"
        fi
    else
        echo ""
    fi

    # Exporting the DB_HOST environment variable by fetching the IP address of your Postgres container:
    export DB_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PG_CONTAINER")

elif [[ $VAR -eq 2 ]]
then
    echo ""
    echo ""
    echo "Installing on Linux..."

    # Installing the required Postgres packages:
    yum install postgresql-server postgresql-contrib

    # Initializing the Postgres installation and configuring it to run as a service
    postgresql-setup initdb
    systemctl enable postgresql.service
    systemctl start postgresql.service

    # Creating a superuser named after your current OS user
    su -c "createuser -s $USER" postgres

    export DB_HOST=localhost

elif [[ $VAR -eq 3 ]]
then
    echo ""
    echo ""
    echo -e "${GREEN}Installing on MacOS...${NC}"
    
    # brew formula for macOS
    brew install postgresql
    brew services start postgres
    export DB_HOST=localhost

else
    echo ""
    echo "Invalid option!"
fi

echo ""
echo "Creating the Database"

export DB_NAME=cuebot_local
export DB_USER=cuebot

echo "Enter your database's password: "
read -s DB_PASS_INPUT
export DB_PASS=$DB_PASS_INPUT


if [[ $IS_DOCKER -eq 0 ]]
then
    createdb $DB_NAME
    createuser $DB_USER --pwprompt
    psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO $DB_USER" $DB_NAME
else
    docker exec -it --user=postgres "$PG_CONTAINER" createdb $DB_NAME
    docker exec -it --user=postgres "$PG_CONTAINER" createuser $DB_USER --pwprompt
    docker exec -it --user=postgres "$PG_CONTAINER" psql -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO $DB_USER" $DB_NAME
fi

echo ""
echo -e "${GREEN}Database successfully created!${NC}"

echo ""
echo -e "${GREEN}Populating the database${NC}"

echo "OPTION 1: Download the published schema and migrate"
echo "OPTION 2: Apply migrations from source"
read -n 1 -p "Select mode of population: " POPULATING_OPT

if [[ $POPULATING_OPT -eq 1 ]]
then
    wget ${BASE_URL}"${VERSION}"/schema-"${VERSION}".sql -P ./db-data/
    wget ${BASE_URL}"${VERSION}"/seed_data-"${VERSION}".sql -P ./db-data/
    
    echo ""
    echo "Populating the database schema and some initial data"
    psql -h $DB_HOST -f ./db-data/schema-"${VERSION}".sql $DB_NAME


    echo ""
    echo "Populating the database with demo data"
    psql -h $DB_HOST -f ./db-data/schema-"${VERSION}".sql $DB_NAME

elif [[ $POPULATING_OPT -eq 2 ]]
then
    brew install flyway ||
    flyway -url=jdbc:postgresql://$DB_HOST/$DB_NAME -user="$USER" -n -locations=filesystem:/cuebot/src/main/resources/conf/ddl/postgres/migrations migrate
    psql -h $DB_HOST -f /cuebot/src/main/resources/conf/ddl/postgres/seed_data.sql $DB_NAME
else
    echo ""
    echo "Invalid option!"
fi

echo ""
echo -e "${GREEN}Database setup completed!${NC}"