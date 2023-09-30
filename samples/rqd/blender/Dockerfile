# Builds on the latest base image of RQD from Docker Hub
FROM opencue/rqd

# Install dependencies to run Blender on the opencue/rqd image
RUN yum -y update
RUN yum -y install \
        bzip2 \
        libfreetype6 \
        libgl1-mesa-dev \
        libXi-devel  \
        mesa-libGLU-devel \
        zlib-devel \
        libXinerama-devel \
        libXrandr-devel

# Set Blender install directory
ARG BLENDER_INSTALL_DIR=/usr/local/blender

# Set Blender download source
ARG BLENDER_DOWNLOAD_SRC=https://download.blender.org/release/Blender3.3/blender-3.3.3-linux-x64.tar.xz

# Download and install Blender
RUN mkdir ${BLENDER_INSTALL_DIR}
RUN curl -SL ${BLENDER_DOWNLOAD_SRC} \
        -o blender.tar.xz

RUN tar -xvf blender.tar.xz \
        -C ${BLENDER_INSTALL_DIR} \
        --strip-components=1

RUN rm blender.tar.xz

# Add Blender path as environment variable
ENV PATH=$PATH:${BLENDER_INSTALL_DIR}

# Verify Blender installation
RUN blender --version
