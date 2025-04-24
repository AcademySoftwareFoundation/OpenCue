# -----------------
# BUILD
# -----------------
FROM gradle:7.6.4-jdk17 AS build

USER gradle

COPY --chown=gradle:gradle ./cuebot /home/gradle/cuebot/
COPY --chown=gradle:gradle ./proto/src /home/gradle/proto/src

WORKDIR /home/gradle/cuebot

RUN gradle build --info --stacktrace

COPY --chown=gradle:gradle VERSION.in ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION
RUN mv ./build/libs/cuebot.jar ./build/libs/cuebot-$(cat ./VERSION)-all.jar


# -----------------
# RPM
# -----------------
FROM jc21/rpmbuild-centos7:latest AS rpm

USER rpmbuilder

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
FROM openjdk:18-slim-buster

# Install curl for healthchecking
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
# Healthcheck that returns exit 0 when succesful
HEALTHCHECK --interval=10s --start-period=20s --timeout=5s CMD curl --http2-prior-knowledge -H 'Content-Type: application/grpc' -H 'te: trailers' --data '' http://localhost:8443/cue.CueInterface/GetSystemStats

ARG CUEBOT_GRPC_CUE_PORT=8443
ARG CUEBOT_GRPC_RQD_PORT=8444

WORKDIR /opt/opencue

COPY --from=build /home/gradle/cuebot/build/libs/cuebot-*-all.jar ./
COPY --from=rpm /home/rpmbuilder/rpmbuild/RPMS/noarch/opencue-cuebot-*.noarch.rpm ./

RUN ln -s $(ls ./cuebot-*-all.jar) ./cuebot-latest.jar

VOLUME ["/opt/opencue/logs"]

ENV grpc_cue_port ${CUEBOT_GRPC_CUE_PORT}
ENV grpc_rqd_port ${CUEBOT_GRPC_RQD_PORT}

EXPOSE $grpc_cue_port

ENTRYPOINT ["java", "-jar", "/opt/opencue/cuebot-latest.jar"]
