FROM centos:7 as base

# Packages needed at both build and runtime.
RUN yum install -y \
      vim \
      java-1.8.0-openjdk.x86_64 \
      java-1.8.0-openjdk-devel.x86_64 \
      libaio \
      which \
    && yum clean all


# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /src

COPY build.gradle .
COPY gradlew .
COPY gradlew.bat .
COPY settings.gradle .
COPY gradle/ ./gradle/

RUN mkdir logs

COPY src/main/resources/ src/main/resources/
COPY src/main/proto/ src/main/proto/
COPY src/main/java/ src/main/java/

RUN chmod -R 777 .
RUN adduser builduser
RUN su -c "./gradlew build --stacktrace" builduser


# -----------------
# TEST
# -----------------
FROM build as test

ARG build_env

ENV CUEBOT_DB_ENGINE=postgres

COPY src/test/ src/test/

RUN if [ "$build_env" == "test" ]; then \
    su -c "./gradlew build --stacktrace" builduser; \
    fi


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN su -c "./gradlew shadowJar --stacktrace" builduser


# -----------------
# RUN
# -----------------
FROM base

ARG CUEBOT_GRPC_CUE_PORT=8443
ARG CUEBOT_GRPC_RQD_PORT=8444

WORKDIR /opt/cue3

COPY --from=package /src/build/libs/cuebot-all.jar /opt/cue3/cuebot.jar

# HEALTHCHECK --start-period=30s --timeout=5s CMD python check_ice.py localhost CueStatic 9019

VOLUME ["/opt/cue3/logs"]

# RQD server
EXPOSE 9018
EXPOSE 9019

ENV grpc_cue_port ${CUEBOT_GRPC_CUE_PORT}
ENV grpc_rqd_port ${CUEBOT_GRPC_RQD_PORT}

EXPOSE $grpc_cue_port
EXPOSE $grpc_rqd_port

ENTRYPOINT ["java", "-jar", "/opt/cue3/cuebot.jar"]
