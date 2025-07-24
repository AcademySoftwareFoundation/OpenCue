FROM --platform=linux/x86_64 rockylinux:9.3

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
    fontconfig \
    freetype \
    gcc \
    libXi \
    libXrender \
    libxkbcommon-x11.x86_64 \
    mesa-libGL \
    python-devel \
    which \
    Xvfb \
    xcb-util-image.x86_64 \
    xcb-util-keysyms.x86_64 \
    xcb-util-renderutil.x86_64 \
    xcb-util-wm.x86_64

RUN yum -y install \
    python\
    python-pip

RUN python3 -m pip install --upgrade pip

COPY LICENSE ./

RUN mkdir /tmp/packages
COPY ${OPENCUE_PROTO_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_PYCUE_PACKAGE_PATH} /tmp/packages/
COPY ${OPENCUE_PYGUI_PACKAGE_PATH} /tmp/packages/

RUN python3 -m pip install /tmp/packages/*.whl
