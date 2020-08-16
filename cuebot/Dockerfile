# -----------------
# BUILD
# -----------------
FROM gradle:6.0.1-jdk11 AS build

USER gradle

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "Cuebot build stage"

COPY --chown=gradle:gradle ./cuebot /home/gradle/cuebot/
COPY --chown=gradle:gradle ./proto /home/gradle/proto/

WORKDIR /home/gradle/cuebot

RUN gradle build --stacktrace --info

COPY --chown=gradle:gradle VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION
RUN mv ./build/libs/cuebot.jar ./build/libs/cuebot-$(cat ./VERSION)-all.jar


# -----------------
# RPM
# -----------------
FROM jc21/rpmbuild-centos7:latest AS rpm

# Random first line after from

USER rpmbuilder

RUN echo "Cuebot RPM Stage"

COPY --chown=rpmbuilder:rpmbuilder LICENSE ./

COPY --from=build \
        --chown=rpmbuilder:rpmbuilder \
        /home/gradle/cuebot/VERSION \
        /home/gradle/cuebot/build/libs/cuebot-*-all.jar \
        /home/gradle/cuebot/deploy/systemd/opencue-cuebot.service \
        /home/gradle/cuebot/deploy/opencue-cuebot \
        /home/gradle/cuebot/packaging/rpm/cuebot.spec \
        /home/gradle/cuebot/packaging/rpm/create_rpm.sh \
        ./

RUN chmod +x create_rpm.sh && ./create_rpm.sh cuebot "$(cat VERSION)"


# -----------------
# RUN
# -----------------
FROM openjdk:11-jre-slim

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "Cuebot runtime stage"

ARG CUEBOT_GRPC_CUE_PORT=8443
ARG CUEBOT_GRPC_RQD_PORT=8444

WORKDIR /opt/opencue

COPY --from=build /home/gradle/cuebot/build/libs/cuebot-*-all.jar ./
COPY --from=rpm /home/rpmbuilder/rpmbuild/RPMS/noarch/opencue-cuebot-*.noarch.rpm ./

RUN ln -s $(ls ./cuebot-*-all.jar) ./cuebot-latest.jar

# TODO(bcipriano) Implement a new GRPC-based health check.
# https://github.com/imageworks/OpenCue/issues/73
# HEALTHCHECK --start-period=30s --timeout=5s CMD python check_ice.py localhost CueStatic 9019

VOLUME ["/opt/opencue/logs"]

ENV grpc_cue_port ${CUEBOT_GRPC_CUE_PORT}
ENV grpc_rqd_port ${CUEBOT_GRPC_RQD_PORT}

EXPOSE $grpc_cue_port

ENTRYPOINT ["java", "-jar", "/opt/opencue/cuebot-latest.jar"]
