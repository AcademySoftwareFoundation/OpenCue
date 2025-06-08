FROM --platform=linux/x86_64 rockylinux:9.3

WORKDIR /opt/opencue

ARG OPENCUE_PROTO_PACKAGE_PATH
ARG OPENCUE_RQD_PACKAGE_PATH
ARG OPENCUE_PYCUE_PACKAGE_PATH
ARG OPENCUE_PYOUTLINE_PACKAGE_PATH
ARG OPENCUE_CUESUBMIT_PACKAGE_PATH
ARG OPENCUE_CUEGUI_PACKAGE_PATH
ARG OPENCUE_CUEADMIN_PACKAGE_PATH

RUN yum -y install \
    epel-release \
    gcc \
    mesa-libGL \
    python-devel

RUN yum -y install \
    python \
    python-pip

RUN python3 -m pip install --upgrade pip

COPY LICENSE ./

RUN mkdir /tmp/packages
COPY ${OPENCUE_PROTO_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_PYCUE_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_PYOUTLINE_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_CUESUBMIT_PACKAGE_PATH} /tmp/packages/

RUN python3 -m pip install /tmp/packages/*.whl
