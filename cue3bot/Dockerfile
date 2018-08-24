FROM centos:7 as base

ARG BUILD_ENV=prod

RUN echo $BUILD_ENV

RUN yum install -y wget \
    && wget https://zeroc.com/download/Ice/3.6/el7/zeroc-ice3.6.repo -P /etc/yum.repos.d \
    && yum clean all

# Packages needed at both build and runtime.
# Configure ICE package repo
RUN yum install -y \
      vim \
      java-1.8.0-openjdk.x86_64 \
      java-1.8.0-openjdk-devel.x86_64 \
      ice-all-runtime \
      ice-all-devel \
      libaio \
      which \
    && yum clean all

# Install Oracle Instant Client
# RPMs should be copied to ../oracle/instantclient/
ENV ORA_INSTANTCLIENT_BASIC_RPM oracle-instantclient12.1-basic-12.1.0.2.0-1.x86_64.rpm
ENV ORA_INSTANTCLIENT_SQLPLUS_RPM oracle-instantclient12.1-sqlplus-12.1.0.2.0-1.x86_64.rpm
COPY oracle/instantclient/$ORA_INSTANTCLIENT_BASIC_RPM project/$ORA_INSTANTCLIENT_BASIC_RPM
COPY oracle/instantclient/$ORA_INSTANTCLIENT_SQLPLUS_RPM project/$ORA_INSTANTCLIENT_SQLPLUS_RPM
RUN rpm -i project/$ORA_INSTANTCLIENT_BASIC_RPM
RUN rpm -i project/$ORA_INSTANTCLIENT_SQLPLUS_RPM


# -----------------
# BUILD
# -----------------
FROM base as build

# Packages needed only at build time.
RUN yum install -y \
      ice-slice-3.6.4 \
      grpc \
      gcc \
      gcc-c++ \
      make \
      libstdc++-static \
    && yum clean all

WORKDIR /src

ARG PROXY_HOSTNAME=localhost

ENV proxy_hostname ${PROXY_HOSTNAME}

COPY shots/ /shots/
COPY tns/ /opt/tns/
COPY bin/sbt* bin/

# Copy just build.properties to specify the version of sbt desired.
COPY project/build.properties project/

RUN mkdir logs

# Download sbt.
RUN wget http://repo.typesafe.com/typesafe/ivy-releases/org.scala-sbt/sbt-launch/0.13.1/sbt-launch.jar -O bin/sbt-launch.jar

RUN bin/sbt clean

COPY build.sbt .

COPY project/ project/
# Resolve dependencies.

RUN bin/sbt update

ENV PROTOBUF_VERSION 3.5.1
RUN curl -#sL "https://github.com/google/protobuf/releases/download/v$PROTOBUF_VERSION/protobuf-java-$PROTOBUF_VERSION.tar.gz" | tar -xz -C /usr/local \
  && cd /usr/local/protobuf-$PROTOBUF_VERSION \
  && ./configure --prefix=/usr \
  && make && make install \
  && rm -rf /usr/local/protobuf-$PROTOBUF_VERSION

ENV LD_LIBRARY_PATH '/usr/lib'

ENV GRPC_JAVA_VERSION 1.14.0
RUN curl -#sL "https://github.com/grpc/grpc-java/archive/v$GRPC_JAVA_VERSION.tar.gz" | tar -xz -C /usr/local \
  && cd /usr/local/grpc-java-$GRPC_JAVA_VERSION/compiler \
  && ../gradlew java_pluginExecutable \
  && cp ./build/exe/java_plugin/protoc-gen-grpc-java /usr/local/bin/protoc-gen-grpc-java \
  && rm -rf /usr/local/grpc-java-$GRPC_JAVA_VERSION

COPY src/main/resources/ src/main/resources/
COPY tns/ /opt/tns/
COPY lib/ lib/
COPY src/main/slice/ src/main/slice/
COPY src/main/proto/ src/main/proto/
COPY src/main/java/ src/main/java/
RUN bin/sbt compile

# -----------------
# TEST
# -----------------
FROM build as test

ARG build_env
ARG cuebot_db_tns=oraxetest
ARG cuebot_db_sys_pwd=foobar32

ENV CUEBOT_DB_TNS=$cuebot_db_tns
ENV CUEBOT_DB_SYS_PWD=$cuebot_db_sys_pwd
ENV CUEBOT_ENABLE_JMS=false

COPY src/test/ src/test/

RUN if [ "$build_env" == "test" ]; \
    then bin/sbt test; \
    fi


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN bin/sbt pack


# -----------------
# RUN
# -----------------
# TODO(cipriano) Switch back to using base image as it does not contain source code.
# This is only needed because we need to run unit tests to populate the cuebot db.
FROM test

WORKDIR /opt/cue3

# Python-Ice
RUN wget https://zeroc.com/download/Ice/3.7/el7/zeroc-ice3.7.repo -P /etc/yum.repos.d
RUN yum install -y \
      ice-all-runtime \
      ice-all-devel \
    && yum clean all

COPY tns/ /opt/tns/
COPY shots/ /shots/
COPY bin/check_ice.py check_ice.py

COPY --from=package /src/target/pack/ /opt/cue3/

# TODO(cipriano) Remove this, once prod db is populated some other way.
COPY populate_db_and_start_cuebot.sh /opt/cue3/

HEALTHCHECK --start-period=30s --timeout=5s CMD python check_ice.py localhost CueStatic 9019

VOLUME ["/opt/cue3/logs"]

# RQD server
EXPOSE 9018
EXPOSE 9019

ENV CUEBOT_ENABLE_JMS=false

ENTRYPOINT ["bin/cuebot"]
