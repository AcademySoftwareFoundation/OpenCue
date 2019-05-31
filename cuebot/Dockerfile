FROM gradle:jdk11 as build

COPY --chown=gradle:gradle ./cuebot /home/gradle/cuebot/
COPY --chown=gradle:gradle ./proto /home/gradle/proto/

WORKDIR /home/gradle/cuebot
RUN gradle build -x test --stacktrace


# -----------------
# RUN
# -----------------
FROM openjdk:11-jre-slim

ARG CUEBOT_GRPC_CUE_PORT=8443
ARG CUEBOT_GRPC_RQD_PORT=8444

RUN mkdir -p /opt/opencue
WORKDIR /opt/opencue

COPY --from=build /home/gradle/cuebot/build/libs/cuebot.jar ./

# TODO(bcipriano) Implement a new GRPC-based health check.
# https://github.com/imageworks/OpenCue/issues/73
# HEALTHCHECK --start-period=30s --timeout=5s CMD python check_ice.py localhost CueStatic 9019

VOLUME ["/opt/opencue/logs"]

ENV grpc_cue_port ${CUEBOT_GRPC_CUE_PORT}
ENV grpc_rqd_port ${CUEBOT_GRPC_RQD_PORT}

EXPOSE $grpc_cue_port

ENTRYPOINT ["java", "-jar", "/opt/opencue/cuebot.jar"]
