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

# Download and install Blender 2.79
RUN mkdir /usr/local/blender
RUN curl -SL https://download.blender.org/release/Blender2.79/blender-2.79-linux-glibc219-x86_64.tar.bz2 \
        -o blender.tar.bz2

RUN tar -jxvf blender.tar.bz2 \
        -C /usr/local/blender \
        --strip-components=1

RUN rm blender.tar.bz2
