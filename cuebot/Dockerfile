FROM centos:7 as base

# Packages needed at both build and runtime.
RUN yum install -y \
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

COPY cuebot/build.gradle cuebot/
COPY cuebot/gradlew cuebot/
COPY cuebot/gradlew.bat cuebot/
COPY cuebot/settings.gradle cuebot/
COPY cuebot/gradle/ cuebot/gradle/

COPY proto/ proto/
COPY cuebot/src/main/resources/ cuebot/src/main/resources/
COPY cuebot/src/main/java/ cuebot/src/main/java/

RUN mkdir logs

# Run as builduser in case tests get run later.
RUN chmod -R 777 .
RUN adduser builduser
RUN su -c "cd cuebot && ./gradlew build --stacktrace" builduser

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION


# -----------------
# TEST
# -----------------
FROM build as test

ENV CUEBOT_DB_ENGINE=postgres

COPY cuebot/src/test/ cuebot/src/test/

# Tests must be run as a non-root user as the embedded Postgres server will not
# work otherwise.
RUN su -c "cd cuebot && ./gradlew build --stacktrace" builduser


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN su -c "cd cuebot && ./gradlew shadowJar --stacktrace" builduser

RUN mv cuebot/build/libs/cuebot-all.jar cuebot/build/libs/cuebot-$(cat ./VERSION)-all.jar


# -----------------
# RUN
# -----------------
FROM base

ARG CUEBOT_GRPC_CUE_PORT=8443
ARG CUEBOT_GRPC_RQD_PORT=8444

WORKDIR /opt/opencue

COPY --from=package /src/cuebot/build/libs/cuebot-*-all.jar ./

RUN ln -s $(ls ./cuebot-*-all.jar) ./cuebot-latest.jar

# TODO(bcipriano) Implement a new GRPC-based health check.
# https://github.com/imageworks/OpenCue/issues/73
# HEALTHCHECK --start-period=30s --timeout=5s CMD python check_ice.py localhost CueStatic 9019

VOLUME ["/opt/opencue/logs"]

ENV grpc_cue_port ${CUEBOT_GRPC_CUE_PORT}
ENV grpc_rqd_port ${CUEBOT_GRPC_RQD_PORT}

EXPOSE $grpc_cue_port

ENTRYPOINT ["java", "-jar", "/opt/opencue/cuebot-latest.jar"]

