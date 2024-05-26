FROM python:3.9.14

WORKDIR /src

RUN yum -y install zip

COPY LICENSE ./
COPY requirements.txt ./

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

RUN versioned_name="OpenCue-Blender-$(cat ./VERSION)-all" \
  && mv pyoutline "${versioned_name}" \
  && zip -r "${versioned_name}.zip" ${versioned_name}/ \
  && mkdir -p /opt/opencue \
  && cp "${versioned_name}.zip" /opt/opencue/