# -----------------
# BUILD
# -----------------
FROM gradle:7.6.4-jdk17 AS build

USER gradle

# Download the plugins and the compile dependencies in their own layer, so a source change
# doesn't download them again. extractIncludeProto needs nothing but the build files.
COPY --chown=gradle:gradle ./cuebot/build.gradle ./cuebot/settings.gradle /home/gradle/cuebot/
WORKDIR /home/gradle/cuebot
RUN gradle extractIncludeProto --no-daemon

COPY --chown=gradle:gradle ./proto/src /home/gradle/proto/src
COPY --chown=gradle:gradle ./cuebot/src/main ./src/main

# The unit tests run in CI (.github/workflows/cuebot.yml), not in the image build.
RUN gradle assemble --no-daemon

ARG BUILD_ID

COPY --chown=gradle:gradle VERSION.in ./
RUN if [ -n "${BUILD_ID}" ]; then echo "${BUILD_ID}" > VERSION; else echo "$(cat VERSION.in)-custom" > VERSION; fi
RUN mv ./build/libs/cuebot.jar ./build/libs/cuebot-$(cat ./VERSION)-all.jar


# -----------------
# RPM, not part of the image: docker build --target packages --output <dir>
# exports the jar and the RPM.
# -----------------
FROM jc21/rpmbuild-centos7:latest AS rpmbuild

USER rpmbuilder

COPY --chown=rpmbuilder:rpmbuilder LICENSE ./

COPY --from=build \
        --chown=rpmbuilder:rpmbuilder \
        /home/gradle/cuebot/VERSION \
        /home/gradle/cuebot/build/libs/cuebot-*-all.jar \
        ./
COPY --chown=rpmbuilder:rpmbuilder \
        ./cuebot/deploy/systemd/opencue-cuebot.service \
        ./cuebot/deploy/opencue-cuebot \
        ./cuebot/packaging/rpm/cuebot.spec \
        ./cuebot/packaging/rpm/create_rpm.sh \
        ./

RUN chmod +x create_rpm.sh && ./create_rpm.sh cuebot "$(cat VERSION)"

FROM scratch AS packages
COPY --from=build /home/gradle/cuebot/build/libs/cuebot-*-all.jar /
COPY --from=rpmbuild /home/rpmbuilder/rpmbuild/RPMS/noarch/opencue-cuebot-*.noarch.rpm /


# -----------------
# RUN
# -----------------
FROM eclipse-temurin:17-jdk-noble

# Install curl for healthchecking
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
# Healthcheck that returns exit 0 when succesful
HEALTHCHECK --interval=10s --start-period=20s --timeout=5s CMD curl --http2-prior-knowledge -H 'Content-Type: application/grpc' -H 'te: trailers' --data '' http://localhost:8443/cue.CueInterface/GetSystemStats

ARG CUEBOT_GRPC_CUE_PORT=8443
ARG CUEBOT_GRPC_RQD_PORT=8444

WORKDIR /opt/opencue

COPY --from=build /home/gradle/cuebot/build/libs/cuebot-*-all.jar ./

RUN ln -s $(ls ./cuebot-*-all.jar) ./cuebot-latest.jar

VOLUME ["/opt/opencue/logs"]

ENV grpc_cue_port ${CUEBOT_GRPC_CUE_PORT}
ENV grpc_rqd_port ${CUEBOT_GRPC_RQD_PORT}

EXPOSE $grpc_cue_port

ENTRYPOINT ["java", "-jar", "/opt/opencue/cuebot-latest.jar"]
