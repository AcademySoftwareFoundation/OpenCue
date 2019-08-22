FROM centos

# Get flyway
RUN ["curl", "-O", "https://repo1.maven.org/maven2/org/flywaydb/flyway-commandline/6.0.0/flyway-commandline-6.0.0-linux-x64.tar.gz"]
RUN ["yum", "install", "-y", "tar", "java-1.8.0-openjdk", "postgresql-jdbc", "nc", "postgresql"]
RUN ["tar", "-xzf", "flyway-commandline-6.0.0-linux-x64.tar.gz"]

WORKDIR flyway-6.0.0

# Copy the postgres driver to its required location
RUN ["cp", "/usr/share/java/postgresql-jdbc.jar", "jars/"]
RUN ["mkdir", "/opt/migrations"]
RUN ["mkdir", "/opt/scripts"]
COPY ./cuebot/src/main/resources/conf/ddl/postgres/migrations /opt/migrations
COPY ./cuebot/src/main/resources/conf/ddl/postgres/demo_data.sql /opt/scripts
COPY ./sandbox/migrate.sh /opt/scripts/

CMD ["/bin/bash"]
