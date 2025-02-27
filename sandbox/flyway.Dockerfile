FROM almalinux:9

ARG FLYWAY_VERSION=9.11.0

# Get flyway
RUN yum install -y tar java-1.8.0-openjdk postgresql-jdbc nc postgresql
RUN curl -O https://repo1.maven.org/maven2/org/flywaydb/flyway-commandline/${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}.tar.gz
RUN tar -xzf flyway-commandline-${FLYWAY_VERSION}.tar.gz

WORKDIR flyway-${FLYWAY_VERSION}

# Copy the postgres driver to its required location
RUN cp /usr/share/java/postgresql-jdbc.jar jars/
RUN mkdir /opt/migrations
RUN mkdir /opt/scripts
COPY ./cuebot/src/main/resources/conf/ddl/postgres/migrations /opt/migrations
COPY ./cuebot/src/main/resources/conf/ddl/postgres/seed_data.sql /opt/scripts
COPY ./sandbox/migrate.sh /opt/scripts/

CMD ["/bin/bash"]
