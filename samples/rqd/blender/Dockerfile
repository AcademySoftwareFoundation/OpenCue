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

# Download and install Blender
RUN mkdir ${BLENDER_INSTALL_DIR}
RUN curl -SL https://download.blender.org/release/Blender3.3/blender-3.3.3-linux-x64.tar.xz \
        -o blender.tar.xz

RUN tar -xvf blender.tar.xz \
        -C ${BLENDER_INSTALL_DIR} \
        --strip-components=1

RUN rm blender.tar.xz

# Verify Blender installation
RUN ${BLENDER_INSTALL_DIR}/blender --version
