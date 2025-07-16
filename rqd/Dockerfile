FROM rockylinux:8.9

WORKDIR /opt/opencue

ARG OPENCUE_PROTO_PACKAGE_PATH
ARG OPENCUE_RQD_PACKAGE_PATH

RUN yum -y install \
  epel-release \
  gcc \
  time

RUN dnf install -y \
  python39 \
  python39-devel \
  python39-pip

RUN python3.9 -m pip install --upgrade pip
RUN python3.9 -m pip install --upgrade setuptools

COPY LICENSE ./

RUN mkdir /tmp/packages
COPY ${OPENCUE_PROTO_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_RQD_PACKAGE_PATH} /tmp/packages/
RUN ls -la /tmp/packages/*
RUN python3.9 -m pip install /tmp/packages/*

RUN mkdir -p /etc/opencue
RUN echo "[Override]" > /etc/opencue/rqd.conf
RUN echo "USE_NIMBY_PYNPUT=false" >> /etc/opencue/rqd.conf

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]
