FROM rockylinux:8.9

WORKDIR /opt/opencue

# Paths to the pre-built python packages.
# They are all defined her but no necessary used to make it simpler between the images
ARG OPENCUE_PROTO_PACKAGE_PATH=/tmp/invalidpath
ARG OPENCUE_RQD_PACKAGE_PATH=/tmp/invalidpath
ARG OPENCUE_PYCUE_PACKAGE_PATH=/tmp/invalidpath
ARG OPENCUE_PYOUTLINE_PACKAGE_PATH=/tmp/invalidpath
ARG OPENCUE_CUESUBMIT_PACKAGE_PATH=/tmp/invalidpath
ARG OPENCUE_CUEGUI_PACKAGE_PATH=/tmp/invalidpath
ARG OPENCUE_CUEADMIN_PACKAGE_PATH=/tmp/invalidpath

RUN yum -y install \
  epel-release \
  gcc \
  time

RUN dnf install -y \
  python39 \
  python39-devel \
  python39-pip

RUN python3.9 -m pip install --upgrade pip

COPY LICENSE ./

RUN mkdir /tmp/packages
COPY ${OPENCUE_PROTO_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_RQD_PACKAGE_PATH} /tmp/packages/

RUN python3.9 -m pip install /tmp/packages/*.whl

RUN mkdir -p /etc/opencue
RUN echo "[Override]" > /etc/opencue/rqd.conf
RUN echo "USE_NIMBY_PYNPUT=false" >> /etc/opencue/rqd.conf

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]
